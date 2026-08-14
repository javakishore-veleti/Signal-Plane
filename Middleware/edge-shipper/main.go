// Edge shipper: runs inside a customer's self hosted estate and ships signals
// outbound to the managed plane (ADR-0007).
//
// The design constraint that matters is not throughput, it is that this process
// opens no listener and requires no inbound firewall rule. Customers who are self
// hosted are usually self hosted because a security function required it, and
// "we need an inbound port" ends that conversation.
//
// Correctness rests on the checkpoint: the position must be durable before the
// batch is acknowledged, so a restart resumes rather than replays or skips.
// Replay is tolerable because signal_id is deterministic and the managed plane
// merges idempotently; silent skipping is not.
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

type Checkpoint struct {
	Position  string    `json:"position"`
	UpdatedAt time.Time `json:"updated_at"`
	Shipped   int64     `json:"shipped_total"`
}

type Store struct{ path string }

func (s *Store) Load() (Checkpoint, error) {
	var cp Checkpoint
	b, err := os.ReadFile(s.path)
	if os.IsNotExist(err) {
		return Checkpoint{Position: ""}, nil
	}
	if err != nil {
		return cp, err
	}
	return cp, json.Unmarshal(b, &cp)
}

// Save writes atomically. A torn checkpoint file is indistinguishable from a lost
// one and would silently restart the estate from the beginning of time.
func (s *Store) Save(cp Checkpoint) error {
	if err := os.MkdirAll(filepath.Dir(s.path), 0o750); err != nil {
		return err
	}
	tmp := s.path + ".tmp"
	b, err := json.Marshal(cp)
	if err != nil {
		return err
	}
	if err := os.WriteFile(tmp, b, 0o640); err != nil {
		return err
	}
	return os.Rename(tmp, s.path)
}

type Batch struct {
	Position string           `json:"position"`
	Signals  []json.RawMessage `json:"signals"`
}

type Reader interface {
	Read(ctx context.Context, from string, max int) (Batch, error)
}

type Shipper struct {
	endpoint string
	token    string
	store    *Store
	reader   Reader
	client   *http.Client
	batch    int
}

// Ship sends one batch and advances the checkpoint only after the managed plane
// has acknowledged durability. Order is load, read, send, then persist.
func (s *Shipper) Ship(ctx context.Context) (int, error) {
	cp, err := s.store.Load()
	if err != nil {
		return 0, fmt.Errorf("load checkpoint: %w", err)
	}

	batch, err := s.reader.Read(ctx, cp.Position, s.batch)
	if err != nil {
		return 0, fmt.Errorf("read: %w", err)
	}
	if len(batch.Signals) == 0 {
		return 0, nil
	}

	body, _ := json.Marshal(batch)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, s.endpoint+"/v1/ingest/batch", bytes.NewReader(body))
	if err != nil {
		return 0, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+s.token)

	resp, err := s.client.Do(req)
	if err != nil {
		return 0, fmt.Errorf("ship: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return 0, fmt.Errorf("ship: managed plane returned %s", resp.Status)
	}

	cp.Position = batch.Position
	cp.UpdatedAt = time.Now().UTC()
	cp.Shipped += int64(len(batch.Signals))
	if err := s.store.Save(cp); err != nil {
		// Batch is durable upstream but the checkpoint is not. On restart this
		// batch is re-sent and merged away by signal_id. Loud, but not lossy.
		return len(batch.Signals), fmt.Errorf("checkpoint save failed, batch will replay: %w", err)
	}
	return len(batch.Signals), nil
}

func (s *Shipper) Run(ctx context.Context, interval time.Duration) {
	backoff := interval
	for {
		n, err := s.Ship(ctx)
		switch {
		case err != nil:
			log.Printf("ship failed: %v (retrying in %s)", err, backoff)
			if backoff < 5*time.Minute {
				backoff *= 2
			}
		default:
			backoff = interval
			if n > 0 {
				log.Printf("shipped %d signals", n)
			}
		}
		select {
		case <-ctx.Done():
			return
		case <-time.After(backoff):
		}
	}
}

func main() {
	endpoint := flag.String("endpoint", os.Getenv("MANAGED_PLANE_URL"), "managed plane ingest endpoint")
	checkpoint := flag.String("checkpoint", "/var/lib/signal-plane/checkpoint.json", "durable checkpoint path")
	interval := flag.Duration("interval", 30*time.Second, "poll interval")
	batch := flag.Int("batch", 500, "signals per batch")
	flag.Parse()

	if *endpoint == "" {
		log.Fatal("endpoint is required; the shipper only ever connects outbound")
	}

	s := &Shipper{
		endpoint: *endpoint,
		token:    os.Getenv("MANAGED_PLANE_TOKEN"),
		store:    &Store{path: *checkpoint},
		reader:   &FileReader{dir: os.Getenv("ESTATE_SPOOL_DIR")},
		client:   &http.Client{Timeout: 30 * time.Second},
		batch:    *batch,
	}
	log.Printf("edge shipper starting, outbound only, target %s", *endpoint)
	s.Run(context.Background(), *interval)
}

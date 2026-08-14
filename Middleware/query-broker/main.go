// Query broker: resolves reads across the managed plane and any remaining self
// hosted estate, so estate migration never requires a cutover (ADR-0008).
//
// Two properties matter more than throughput here:
//
//   Merge is by signal_id, which is a deterministic v5 UUID over
//   (tenant, adapter, native id). The same source event ingested by both estates
//   collapses to one result, so the backfill window does not produce duplicates.
//
//   Partial results are reported, never hidden. If an estate does not answer, the
//   response says so. A console that silently returns half the data during an
//   investigation is worse than one that returns an error.
package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"sort"
	"sync"
	"time"
)

type Signal struct {
	SignalID   string         `json:"signal_id"`
	TenantID   string         `json:"tenant_id"`
	SubjectID  string         `json:"subject_id"`
	OccurredAt time.Time      `json:"occurred_at"`
	Category   string         `json:"category"`
	SignalType string         `json:"signal_type"`
	Estate     string         `json:"estate"`
	Attributes map[string]any `json:"attributes,omitempty"`
}

type Query struct {
	TenantID  string
	SubjectID string
	From, To  time.Time
	Limit     int
}

// Estate is one queryable store. The managed plane and each self hosted
// deployment implement the same interface, which is what lets the broker treat
// migration as a routing concern rather than a data concern.
type Estate interface {
	Name() string
	Kind() string // "managed" or "self_hosted"
	Query(ctx context.Context, q Query) ([]Signal, error)
}

type EstateStatus struct {
	Name    string `json:"name"`
	Kind    string `json:"kind"`
	Status  string `json:"status"` // ok | timeout | error
	Count   int    `json:"count"`
	Message string `json:"message,omitempty"`
}

type Response struct {
	Signals  []Signal       `json:"signals"`
	Estates  []EstateStatus `json:"estates"`
	Complete bool           `json:"complete"`
	Merged   int            `json:"duplicates_merged"`
}

type Broker struct {
	estates  []Estate
	deadline time.Duration
}

func NewBroker(deadline time.Duration, estates ...Estate) *Broker {
	return &Broker{estates: estates, deadline: deadline}
}

func (b *Broker) Fetch(ctx context.Context, q Query) Response {
	ctx, cancel := context.WithTimeout(ctx, b.deadline)
	defer cancel()

	var (
		mu       sync.Mutex
		wg       sync.WaitGroup
		statuses = make([]EstateStatus, len(b.estates))
		byID     = map[string]Signal{}
		dupes    int
	)

	for i, e := range b.estates {
		wg.Add(1)
		go func(i int, e Estate) {
			defer wg.Done()
			st := EstateStatus{Name: e.Name(), Kind: e.Kind(), Status: "ok"}
			sigs, err := e.Query(ctx, q)
			switch {
			case err != nil:
				st.Status, st.Message = "error", err.Error()
			case ctx.Err() != nil:
				st.Status, st.Message = "timeout", ctx.Err().Error()
			default:
				st.Count = len(sigs)
			}

			mu.Lock()
			defer mu.Unlock()
			statuses[i] = st
			for _, s := range sigs {
				if existing, seen := byID[s.SignalID]; seen {
					dupes++
					// Managed plane wins: it carries current enrichment.
					if existing.Estate == "managed" {
						continue
					}
				}
				byID[s.SignalID] = s
			}
		}(i, e)
	}
	wg.Wait()

	out := make([]Signal, 0, len(byID))
	for _, s := range byID {
		out = append(out, s)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].OccurredAt.After(out[j].OccurredAt) })
	if q.Limit > 0 && len(out) > q.Limit {
		out = out[:q.Limit]
	}

	complete := true
	for _, st := range statuses {
		if st.Status != "ok" {
			complete = false
		}
	}
	return Response{Signals: out, Estates: statuses, Complete: complete, Merged: dupes}
}

func (b *Broker) handler(w http.ResponseWriter, r *http.Request) {
	q := Query{
		TenantID:  r.URL.Query().Get("tenant_id"),
		SubjectID: r.URL.Query().Get("subject_id"),
		Limit:     100,
	}
	if q.TenantID == "" {
		http.Error(w, `{"error":"tenant_id is required"}`, http.StatusBadRequest)
		return
	}
	resp := b.Fetch(r.Context(), q)
	w.Header().Set("Content-Type", "application/json")
	if !resp.Complete {
		// Surfaced as a header so the console can render a partial results banner
		// without parsing the body first.
		w.Header().Set("X-Results-Partial", "true")
	}
	_ = json.NewEncoder(w).Encode(resp)
}

func main() {
	port := os.Getenv("QUERY_BROKER_PORT")
	if port == "" {
		port = "8081"
	}
	b := NewBroker(2*time.Second,
		NewStubEstate("managed-plane", "managed", 40*time.Millisecond),
		NewStubEstate("estate-legacy-01", "self_hosted", 300*time.Millisecond),
	)
	http.HandleFunc("/v1/signals", b.handler)
	http.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Write([]byte(`{"status":"ok"}`))
	})
	log.Printf("query broker listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

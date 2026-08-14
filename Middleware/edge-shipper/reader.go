package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
)

// FileReader reads spooled envelopes from the estate's local disk. Position is the
// last filename consumed, which is monotonic because the spool is time ordered.
type FileReader struct{ dir string }

func (r *FileReader) Read(ctx context.Context, from string, max int) (Batch, error) {
	if r.dir == "" {
		return Batch{}, nil
	}
	entries, err := os.ReadDir(r.dir)
	if err != nil {
		if os.IsNotExist(err) {
			return Batch{}, nil
		}
		return Batch{}, err
	}

	names := make([]string, 0, len(entries))
	for _, e := range entries {
		if !e.IsDir() && filepath.Ext(e.Name()) == ".json" && e.Name() > from {
			names = append(names, e.Name())
		}
	}
	sort.Strings(names)
	if len(names) > max {
		names = names[:max]
	}

	batch := Batch{}
	for _, n := range names {
		b, err := os.ReadFile(filepath.Join(r.dir, n))
		if err != nil {
			return batch, err
		}
		batch.Signals = append(batch.Signals, json.RawMessage(b))
		batch.Position = n
	}
	return batch, nil
}

package main

import (
	"context"
	"fmt"
	"time"
)

// StubEstate stands in for a real store so the read path can be exercised with no
// infrastructure. Swap for an index backed implementation without touching Broker.
type StubEstate struct {
	name    string
	kind    string
	latency time.Duration
}

func NewStubEstate(name, kind string, latency time.Duration) *StubEstate {
	return &StubEstate{name: name, kind: kind, latency: latency}
}

func (s *StubEstate) Name() string { return s.name }
func (s *StubEstate) Kind() string { return s.kind }

func (s *StubEstate) Query(ctx context.Context, q Query) ([]Signal, error) {
	select {
	case <-time.After(s.latency):
	case <-ctx.Done():
		return nil, ctx.Err()
	}

	now := time.Now().UTC()
	out := make([]Signal, 0, 3)
	for i := 0; i < 3; i++ {
		// Index 0 is intentionally shared across estates: during backfill the same
		// source event exists in both, and must merge to one result.
		id := fmt.Sprintf("shared-signal-%d", i)
		if i > 0 {
			id = fmt.Sprintf("%s-signal-%d", s.name, i)
		}
		out = append(out, Signal{
			SignalID:   id,
			TenantID:   q.TenantID,
			SubjectID:  q.SubjectID,
			OccurredAt: now.Add(-time.Duration(i) * time.Minute),
			Category:   "file_action",
			SignalType: "file_action.modify",
			Estate:     s.kind,
		})
	}
	return out, nil
}

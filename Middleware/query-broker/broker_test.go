package main

import (
	"context"
	"testing"
	"time"
)

func TestDuplicatesMergeAcrossEstates(t *testing.T) {
	b := NewBroker(time.Second,
		NewStubEstate("managed-plane", "managed", 0),
		NewStubEstate("estate-legacy-01", "self_hosted", 0),
	)
	resp := b.Fetch(context.Background(), Query{TenantID: "tenant-demo"})
	if resp.Merged == 0 {
		t.Fatal("expected the shared signal to be merged; backfill would double count")
	}
	seen := map[string]bool{}
	for _, s := range resp.Signals {
		if seen[s.SignalID] {
			t.Fatalf("duplicate signal_id %s survived the merge", s.SignalID)
		}
		seen[s.SignalID] = true
	}
}

func TestSlowEstateReportsPartialRatherThanHanging(t *testing.T) {
	b := NewBroker(50*time.Millisecond,
		NewStubEstate("managed-plane", "managed", 0),
		NewStubEstate("estate-legacy-01", "self_hosted", 2*time.Second),
	)
	start := time.Now()
	resp := b.Fetch(context.Background(), Query{TenantID: "tenant-demo"})
	if elapsed := time.Since(start); elapsed > time.Second {
		t.Fatalf("broker waited %v; deadline should have cut it off", elapsed)
	}
	if resp.Complete {
		t.Fatal("results are partial and must be reported as such")
	}
	if len(resp.Signals) == 0 {
		t.Fatal("the healthy estate should still have returned results")
	}
}

func TestResultsAreOrderedNewestFirst(t *testing.T) {
	b := NewBroker(time.Second, NewStubEstate("managed-plane", "managed", 0))
	resp := b.Fetch(context.Background(), Query{TenantID: "tenant-demo"})
	for i := 1; i < len(resp.Signals); i++ {
		if resp.Signals[i].OccurredAt.After(resp.Signals[i-1].OccurredAt) {
			t.Fatal("signals must be newest first")
		}
	}
}

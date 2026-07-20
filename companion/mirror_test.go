package main

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestMirrorObserverStreamsOnlyNewBytes(t *testing.T) {
	path := filepath.Join(t.TempDir(), "transcript")
	if err := os.WriteFile(path, []byte("first\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	observer := newMirrorObserver(path, 64)
	got, err := observer.readNew()
	if err != nil || string(got) != "first\n" {
		t.Fatalf("first read = %q, %v", got, err)
	}
	got, err = observer.readNew()
	if err != nil || len(got) != 0 {
		t.Fatalf("duplicate read = %q, %v", got, err)
	}
	file, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		t.Fatal(err)
	}
	_, _ = file.WriteString("second\n")
	_ = file.Close()
	got, err = observer.readNew()
	if err != nil || string(got) != "second\n" {
		t.Fatalf("append read = %q, %v", got, err)
	}
}

func TestMirrorObserverRecoversFromTruncation(t *testing.T) {
	path := filepath.Join(t.TempDir(), "transcript")
	if err := os.WriteFile(path, []byte("old\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	observer := newMirrorObserver(path, 64)
	_, _ = observer.readNew()
	if err := os.WriteFile(path, []byte("new\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	got, err := observer.readNew()
	if err != nil || string(got) != "new\n" {
		t.Fatalf("truncation recovery = %q, %v", got, err)
	}
}

func TestMirrorObserverBoundedBatchDoesNotDropTail(t *testing.T) {
	path := filepath.Join(t.TempDir(), "transcript")
	if err := os.WriteFile(path, []byte("0123456789"), 0o600); err != nil {
		t.Fatal(err)
	}
	observer := newMirrorObserver(path, 4)
	var all []byte
	for len(all) < 10 {
		got, err := observer.readNew()
		if err != nil {
			t.Fatal(err)
		}
		all = append(all, got...)
	}
	if string(all) != "0123456789" {
		t.Fatalf("bounded stream = %q", all)
	}
}

func TestMirrorObserverReportsSourceDisappearance(t *testing.T) {
	path := filepath.Join(t.TempDir(), "transcript")
	observer := newMirrorObserver(path, 64)
	_, err := observer.readNew()
	if !errors.Is(err, errMirrorSourceUnavailable) {
		t.Fatalf("error = %v", err)
	}
}

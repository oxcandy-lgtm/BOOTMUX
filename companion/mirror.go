package main

import (
	"bytes"
	"errors"
	"io"
	"os"
)

var errMirrorSourceUnavailable = errors.New("mirror_source_unavailable")

type mirrorObserver struct {
	path    string
	offset  int64
	batch   int64
	modTime int64
	prefix  []byte
}

func newMirrorObserver(path string, batch int) *mirrorObserver {
	if batch <= 0 {
		batch = defaultMirrorBatchBytes
	}
	return &mirrorObserver{path: path, batch: int64(batch)}
}

func (o *mirrorObserver) readNew() ([]byte, error) {
	info, err := os.Stat(o.path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, errMirrorSourceUnavailable
		}
		return nil, err
	}
	modTime := info.ModTime().UnixNano()
	if info.Size() < o.offset || (info.Size() == o.offset && modTime != o.modTime) {
		o.offset = 0
	}
	file, err := os.Open(o.path)
	if err != nil {
		return nil, errMirrorSourceUnavailable
	}
	defer file.Close()
	if info.Size() == o.offset && len(o.prefix) > 0 {
		currentPrefix := make([]byte, len(o.prefix))
		if _, err := io.ReadFull(file, currentPrefix); err == nil && !bytes.Equal(currentPrefix, o.prefix) {
			o.offset = 0
		}
		if _, err := file.Seek(o.offset, io.SeekStart); err != nil {
			return nil, err
		}
	}
	if _, err := file.Seek(o.offset, io.SeekStart); err != nil {
		return nil, err
	}
	data, err := io.ReadAll(io.LimitReader(file, o.batch))
	if err != nil {
		return nil, err
	}
	o.offset += int64(len(data))
	o.modTime = modTime
	if len(o.prefix) == 0 && len(data) > 0 {
		o.prefix = append([]byte(nil), data...)
	}
	return data, nil
}

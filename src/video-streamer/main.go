// Package main contains an example.
package main

import (
	"crypto/tls"
	"log"
	"matek-video-streamer/internal/server"
	"matek-video-streamer/internal/streamer"
	"matek-video-streamer/internal/utils"
	"time"

	"github.com/bluenviron/gortsplib/v4"
	"github.com/bluenviron/gortsplib/v4/pkg/description"
	"github.com/bluenviron/gortsplib/v4/pkg/format"
)

// This example shows how to
// 1. create a RTSP server which accepts plain connections.
// 2. read from disk a MPEG-TS file which contains a H264 track.
// 3. serve the content of the file to all connected readers.

func main() {
	h := &server.ServerHandler{}

	cert, err := tls.LoadX509KeyPair("server.crt", "server.key")
	if err != nil {
		panic(err)
	}

	// prevent clients from connecting to the server until the stream is properly set up
	h.Mutex.Lock()

	// create the server
	h.Server = &gortsplib.Server{
		Handler:           h,
		TLSConfig:         &tls.Config{Certificates: []tls.Certificate{cert}},
		RTSPAddress:       "0.0.0.0:8554",
		UDPRTPAddress:     "0.0.0.0:8000",
		UDPRTCPAddress:    "0.0.0.0:8001",
		MulticastIPRange:  "224.1.0.0/16",
		MulticastRTPPort:  8002,
		MulticastRTCPPort: 8003,
	}

	// start the server
	err = h.Server.Start()
	if err != nil {
		panic(err)
	}
	defer h.Server.Close()

	h264Params, err := utils.ExtractH264ParametersFromPipe("/tmp/camera_stream", 10*time.Second)

	if err != nil {
		log.Fatalf("Error: Failed to extract H.264 parameter: %v", err)
	}

	// create a RTSP description that contains a H264 format
	desc := &description.Session{
		Medias: []*description.Media{{
			Type: description.MediaTypeVideo,
			Formats: []format.Format{&format.H264{
				PayloadTyp:        96,
				PacketizationMode: 1,
				SPS:               h264Params.SPS,
				PPS:               h264Params.PPS,
			}},
		}},
	}

	// create a server stream
	h.Stream = &gortsplib.ServerStream{
		Server: h.Server,
		Desc:   desc,
	}
	err = h.Stream.Initialize()
	if err != nil {
		panic(err)
	}
	defer h.Stream.Close()

	// create file streamer
	r := streamer.New(h.Stream, "/tmp/camera_stream")
	err = r.Initialize()
	if err != nil {
		panic(err)
	}
	defer r.Close()

	// allow clients to connect
	h.Mutex.Unlock()
	// remove pipe file after the server is ready

	err = utils.RemovePipe("/tmp/camera_stream")
	if err != nil {
		log.Printf("Warning: Failed to remove pipe file: %v", err)
	}

	// wait until a fatal error
	log.Printf("server is ready on %s", h.Server.RTSPAddress)
	panic(h.Server.Wait())
}

// Package main contains an example.
package main

import (
	"crypto/tls"
	"log"
	"matek-video-streamer/internal/server"
	"matek-video-streamer/internal/streamer"
	"matek-video-streamer/internal/utils"
	"os"
	"time"

	"github.com/bluenviron/gortsplib/v4"
	"github.com/bluenviron/gortsplib/v4/pkg/description"
	"github.com/bluenviron/gortsplib/v4/pkg/format"
	"github.com/urfave/cli/v2"
)

// This example shows how to
// 1. create a RTSP server which accepts plain connections.
// 2. read from disk a MPEG-TS file which contains a H264 track.
// 3. serve the content of the file to all connected readers.

func main() {
	app := &cli.App{
		Name:  "matek-video-streamer",
		Usage: "RTSP video streaming server",
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:    "cert",
				Aliases: []string{"c"},
				Value:   "scripts/server.crt",
				Usage:   "Path to TLS certificate file",
			},
			&cli.StringFlag{
				Name:    "key",
				Aliases: []string{"k"},
				Value:   "scripts/server.key",
				Usage:   "Path to TLS private key file",
			},
			&cli.StringFlag{
				Name:    "pipe",
				Aliases: []string{"p"},
				Value:   "./camera_stream",
				Usage:   "Path to camera stream pipe",
			},
			// &cli.StringFlag{
			// 	Name:    "stream-pipe",
			// 	Aliases: []string{"s"},
			// 	Value:   "/tmp/camera_stream",
			// 	Usage:   "Path to stream pipe",
			// },
		},
		Action: runServer,
	}

	if err := app.Run(os.Args); err != nil {
		log.Fatal(err)
	}
}

func runServer(c *cli.Context) error {
	certPath := c.String("cert")
	keyPath := c.String("key")
	cameraPipePath := c.String("pipe")
	// streamPipePath := c.String("stream-pipe")

	h := &server.ServerHandler{}

	cert, err := tls.LoadX509KeyPair(certPath, keyPath)
	if err != nil {
		return err
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
		return err
	}
	defer h.Server.Close()

	h264Params, err := utils.ExtractH264ParametersFromPipe(cameraPipePath, 10*time.Second)

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
		return err
	}
	defer h.Stream.Close()

	// create file streamer
	r := streamer.New(h.Stream, cameraPipePath)
	err = r.Initialize()
	if err != nil {
		return err
	}
	defer r.Close()

	// allow clients to connect
	h.Mutex.Unlock()
	// remove pipe file after the server is ready

	// err = utils.RemovePipe("/tmp/camera_stream")
	// if err != nil {
	// 	log.Printf("Warning: Failed to remove pipe file: %v", err)
	// }

	// wait until a fatal error
	log.Printf("server is ready on %s", h.Server.RTSPAddress)
	panic(h.Server.Wait())
}

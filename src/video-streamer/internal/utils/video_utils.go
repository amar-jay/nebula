package utils

import (
	"bufio"
	"context"
	"encoding/hex"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/bluenviron/mediacommon/v2/pkg/codecs/h264"
)

// H264Parameters holds SPS and PPS data
type H264Parameters struct {
	SPS []byte
	PPS []byte
}

// ExtractH264ParametersFromStream extracts SPS and PPS from an H.264 stream using mediacommon
// This is the most efficient method for live streams
func ExtractH264ParametersFromStream(filePath string) (*H264Parameters, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open file: %v", err)
	}
	defer file.Close()

	reader := bufio.NewReader(file)
	params := &H264Parameters{}

	// Read the first few chunks to find SPS/PPS
	buffer := make([]byte, 8192) // 8KB buffer
	bytesRead := 0
	maxBytes := 1024 * 1024 // Read max 1MB to find parameters

	for bytesRead < maxBytes {
		n, err := reader.Read(buffer)
		if err != nil && err != io.EOF {
			return nil, fmt.Errorf("failed to read file: %v", err)
		}
		if n == 0 {
			break
		}

		// Parse NAL units using mediacommon
		var annexB h264.AnnexB
		err = annexB.Unmarshal(buffer[:n])
		if err != nil {
			// If parsing fails, continue reading more data
			bytesRead += n
			continue
		}

		for _, nalu := range annexB {
			nalType := h264.NALUType(nalu[0] & 0x1F)

			switch nalType {
			case h264.NALUTypeSPS:
				if params.SPS == nil {
					params.SPS = make([]byte, len(nalu))
					copy(params.SPS, nalu)
				}
			case h264.NALUTypePPS:
				if params.PPS == nil {
					params.PPS = make([]byte, len(nalu))
					copy(params.PPS, nalu)
				}
			}

			// If we have both SPS and PPS, we're done
			if params.SPS != nil && params.PPS != nil {
				return params, nil
			}
		}

		bytesRead += n
		if err == io.EOF {
			break
		}
	}

	if params.SPS == nil {
		return nil, fmt.Errorf("SPS not found in stream")
	}
	if params.PPS == nil {
		return nil, fmt.Errorf("PPS not found in stream")
	}

	return params, nil
}

// ExtractH264ParametersFromPipe extracts SPS and PPS from a named pipe or FIFO
// This is designed for real-time streams, especially MPEG-TS format
func ExtractH264ParametersFromPipe(pipePath string, timeout time.Duration) (*H264Parameters, error) {
	log.Printf("Opening named pipe: %s", pipePath)

	// Check if pipe exists first
	if _, err := os.Stat(pipePath); os.IsNotExist(err) {
		return nil, fmt.Errorf("named pipe does not exist: %s", pipePath)
	}

	// Set up timeout context
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	// Channel for results
	done := make(chan *H264Parameters, 1)
	errChan := make(chan error, 1)

	go func() {
		defer func() {
			if r := recover(); r != nil {
				errChan <- fmt.Errorf("panic in pipe reader: %v", r)
			}
		}()

		// Open the pipe for reading with a shorter timeout for opening
		file, err := os.OpenFile(pipePath, os.O_RDONLY, 0)
		if err != nil {
			errChan <- fmt.Errorf("failed to open pipe: %v", err)
			return
		}
		defer file.Close()

		log.Printf("Successfully opened pipe, waiting for data...")

		reader := bufio.NewReader(file)
		params := &H264Parameters{}
		buffer := make([]byte, 8192)
		accumulated := make([]byte, 0, 65536)

		bytesRead := 0
		noDataCount := 0
		maxNoDataCount := 100 // Maximum consecutive reads with no data

		for {
			// Check if context is cancelled
			select {
			case <-ctx.Done():
				errChan <- fmt.Errorf("timeout while reading from pipe")
				return
			default:
			}

			// Set a shorter read timeout to allow checking context cancellation
			file.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
			n, err := reader.Read(buffer)

			if err != nil {
				if os.IsTimeout(err) {
					noDataCount++
					if noDataCount > maxNoDataCount {
						errChan <- fmt.Errorf("no data received from pipe after %d attempts", maxNoDataCount)
						return
					}
					continue
				} else if err != io.EOF {
					errChan <- fmt.Errorf("failed to read from pipe: %v", err)
					return
				}
			}

			if n == 0 {
				noDataCount++
				if noDataCount > maxNoDataCount {
					errChan <- fmt.Errorf("no data received from pipe after %d attempts", maxNoDataCount)
					return
				}
				time.Sleep(100 * time.Millisecond)
				continue
			}

			// Reset no data counter when we get data
			noDataCount = 0
			bytesRead += n
			accumulated = append(accumulated, buffer[:n]...)

			if bytesRead%25000 == 0 {
				log.Printf("Read %d bytes from pipe, accumulated %d bytes", bytesRead, len(accumulated))
			}

			// Try parsing when we have sufficient data
			if len(accumulated) >= 1024 {
				// Method 1: Try direct H.264 Annex-B parsing
				if params.SPS == nil || params.PPS == nil {
					extractedParams := tryParseH264Parameters(accumulated)
					if extractedParams != nil {
						if extractedParams.SPS != nil && params.SPS == nil {
							params.SPS = extractedParams.SPS
							log.Printf("Found SPS in pipe stream (%d bytes)", len(params.SPS))
						}
						if extractedParams.PPS != nil && params.PPS == nil {
							params.PPS = extractedParams.PPS
							log.Printf("Found PPS in pipe stream (%d bytes)", len(params.PPS))
						}
					}
				}

				// Method 2: Try MPEG-TS parsing if direct parsing fails
				if (params.SPS == nil || params.PPS == nil) && len(accumulated) >= 4096 {
					extractedParams := tryParseMPEGTSH264(accumulated)
					if extractedParams != nil {
						if extractedParams.SPS != nil && params.SPS == nil {
							params.SPS = extractedParams.SPS
							log.Printf("Found SPS in MPEG-TS stream (%d bytes)", len(params.SPS))
						}
						if extractedParams.PPS != nil && params.PPS == nil {
							params.PPS = extractedParams.PPS
							log.Printf("Found PPS in MPEG-TS stream (%d bytes)", len(params.PPS))
						}
					}
				}

				// If we have both, we're done
				if params.SPS != nil && params.PPS != nil {
					log.Printf("Successfully found both SPS and PPS from pipe")
					done <- params
					return
				}

				// Keep memory usage reasonable
				if len(accumulated) > 32768 {
					accumulated = accumulated[len(accumulated)-16384:]
				}
			}
		}
	}()

	select {
	case params := <-done:
		return params, nil
	case err := <-errChan:
		return nil, err
	case <-ctx.Done():
		return nil, fmt.Errorf("timeout waiting for SPS/PPS parameters from pipe (waited %v)", timeout)
	}
}

// tryParseH264Parameters attempts to parse H.264 parameters from raw data
func tryParseH264Parameters(data []byte) *H264Parameters {
	params := &H264Parameters{}

	// Look for NAL unit start codes
	for i := 0; i < len(data)-4; i++ {
		// Check for 4-byte start code (0x00000001)
		if data[i] == 0x00 && data[i+1] == 0x00 && data[i+2] == 0x00 && data[i+3] == 0x01 {
			nalStart := i + 4
			if nalStart >= len(data) {
				continue
			}

			nalType := data[nalStart] & 0x1F

			// Find end of NAL unit
			nalEnd := nalStart + 1
			for nalEnd < len(data)-3 {
				if data[nalEnd] == 0x00 && data[nalEnd+1] == 0x00 &&
					(data[nalEnd+2] == 0x01 || (data[nalEnd+2] == 0x00 && nalEnd+3 < len(data) && data[nalEnd+3] == 0x01)) {
					break
				}
				nalEnd++
			}

			nalData := data[nalStart:nalEnd]

			switch nalType {
			case 7: // SPS
				if params.SPS == nil && len(nalData) > 3 {
					params.SPS = make([]byte, len(nalData))
					copy(params.SPS, nalData)
				}
			case 8: // PPS
				if params.PPS == nil && len(nalData) > 3 {
					params.PPS = make([]byte, len(nalData))
					copy(params.PPS, nalData)
				}
			}

			if params.SPS != nil && params.PPS != nil {
				return params
			}
		}

		// Also check for 3-byte start code (0x000001)
		if data[i] == 0x00 && data[i+1] == 0x00 && data[i+2] == 0x01 {
			nalStart := i + 3
			if nalStart >= len(data) {
				continue
			}

			nalType := data[nalStart] & 0x1F

			// Find end of NAL unit
			nalEnd := nalStart + 1
			for nalEnd < len(data)-2 {
				if data[nalEnd] == 0x00 && data[nalEnd+1] == 0x00 &&
					(nalEnd+2 < len(data) && data[nalEnd+2] == 0x01) {
					break
				}
				nalEnd++
			}

			nalData := data[nalStart:nalEnd]

			switch nalType {
			case 7: // SPS
				if params.SPS == nil && len(nalData) > 3 {
					params.SPS = make([]byte, len(nalData))
					copy(params.SPS, nalData)
				}
			case 8: // PPS
				if params.PPS == nil && len(nalData) > 3 {
					params.PPS = make([]byte, len(nalData))
					copy(params.PPS, nalData)
				}
			}

			if params.SPS != nil && params.PPS != nil {
				return params
			}
		}
	}

	if params.SPS != nil || params.PPS != nil {
		return params
	}
	return nil
}

// tryParseMPEGTSH264 attempts to extract H.264 data from MPEG-TS format
func tryParseMPEGTSH264(data []byte) *H264Parameters {
	// MPEG-TS packets are 188 bytes each, starting with 0x47
	params := &H264Parameters{}

	for i := 0; i < len(data)-188; i++ {
		if data[i] == 0x47 { // TS packet sync byte
			// Extract payload from TS packet
			tsPacket := data[i : i+188]

			// Skip TS header (4 bytes minimum)
			payloadStart := 4

			// Check for adaptation field
			adaptationControl := (tsPacket[3] >> 4) & 0x03
			if adaptationControl == 2 || adaptationControl == 3 {
				if payloadStart < len(tsPacket) {
					adaptationLength := int(tsPacket[payloadStart])
					payloadStart += 1 + adaptationLength
				}
			}

			if payloadStart >= len(tsPacket) {
				continue
			}

			payload := tsPacket[payloadStart:]

			// Try to extract H.264 parameters from payload
			extractedParams := tryParseH264Parameters(payload)
			if extractedParams != nil {
				if extractedParams.SPS != nil && params.SPS == nil {
					params.SPS = extractedParams.SPS
				}
				if extractedParams.PPS != nil && params.PPS == nil {
					params.PPS = extractedParams.PPS
				}

				if params.SPS != nil && params.PPS != nil {
					return params
				}
			}
		}
	}

	if params.SPS != nil || params.PPS != nil {
		return params
	}
	return nil
}

// ValidateH264Parameters validates SPS and PPS parameters using mediacommon
func ValidateH264Parameters(params *H264Parameters) error {
	if params == nil {
		return fmt.Errorf("parameters are nil")
	}

	if len(params.SPS) == 0 {
		return fmt.Errorf("SPS is empty")
	}

	if len(params.PPS) == 0 {
		return fmt.Errorf("PPS is empty")
	}

	// Validate SPS using mediacommon parser
	var sps h264.SPS
	err := sps.Unmarshal(params.SPS)
	if err != nil {
		return fmt.Errorf("invalid SPS: %v", err)
	}

	// Basic validation of SPS fields
	if sps.PicWidthInMbsMinus1 == 0 || sps.PicHeightInMapUnitsMinus1 == 0 {
		return fmt.Errorf("invalid SPS dimensions")
	}

	return nil
}

// ExtractH264Parameters extracts SPS and PPS from a video file using FFmpeg
func ExtractH264Parameters(filePath string) (*H264Parameters, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 1000*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "ffmpeg",
		"-i", filePath,
		"-c:v", "copy",
		"-bsf:v", "h264_mp4toannexb",
		"-f", "h264",
		"-y",
		"pipe:1",
	)

	output, err := cmd.Output()
	if ctx.Err() == context.DeadlineExceeded {
		return nil, fmt.Errorf("timeout while extracting SPS/PPS")
	}
	if err != nil {
		return nil, fmt.Errorf("failed to extract H.264 parameters: %v", err)
	}

	return parseH264Parameters(output)
}

// ExtractH264ParametersFromHex extracts SPS and PPS using ffprobe to get hex output
func ExtractH264ParametersFromHex(filePath string) (*H264Parameters, error) {
	if !strings.HasSuffix(filePath, ".mp4") && !strings.HasSuffix(filePath, ".flv") {
		return nil, fmt.Errorf("extradata not available for non-container format: %s", filePath)
	}

	// Use ffprobe to get codec extradata in hex format
	cmd := exec.Command("ffprobe",
		"-v", "quiet",
		"-show_entries", "stream=codec_name,extradata",
		"-select_streams", "v:0",
		"-of", "csv=p=0",
		filePath,
	)

	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to probe video file: %v", err)
	}

	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		if strings.Contains(line, "h264") && strings.Contains(line, ",") {
			parts := strings.Split(line, ",")
			if len(parts) >= 2 {
				hexData := strings.TrimSpace(parts[1])
				if hexData != "" {
					data, err := hex.DecodeString(hexData)
					if err != nil {
						continue
					}
					return parseH264Parameters(data)
				}
			}
		}
	}

	return nil, fmt.Errorf("no H.264 extradata found")
}

// parseH264Parameters parses raw H.264 data to extract SPS and PPS
func parseH264Parameters(data []byte) (*H264Parameters, error) {
	params := &H264Parameters{}

	// Look for NAL units starting with 0x00000001 or 0x000001
	i := 0
	for i < len(data) {
		// Find start code
		if i+4 < len(data) && data[i] == 0x00 && data[i+1] == 0x00 && data[i+2] == 0x00 && data[i+3] == 0x01 {
			i += 4
		} else if i+3 < len(data) && data[i] == 0x00 && data[i+1] == 0x00 && data[i+2] == 0x01 {
			i += 3
		} else {
			i++
			continue
		}

		if i >= len(data) {
			break
		}

		// Get NAL unit type (first 5 bits of the byte after start code)
		nalType := data[i] & 0x1F

		// Find end of this NAL unit
		end := i + 1
		for end < len(data) {
			if end+3 < len(data) && data[end] == 0x00 && data[end+1] == 0x00 && data[end+2] == 0x01 {
				break
			}
			if end+4 < len(data) && data[end] == 0x00 && data[end+1] == 0x00 && data[end+2] == 0x00 && data[end+3] == 0x01 {
				break
			}
			end++
		}

		nalData := data[i:end]

		switch nalType {
		case 7: // SPS
			params.SPS = nalData
		case 8: // PPS
			params.PPS = nalData
		}

		i = end
	}

	if len(params.SPS) == 0 {
		return nil, fmt.Errorf("SPS not found")
	}
	if len(params.PPS) == 0 {
		return nil, fmt.Errorf("PPS not found")
	}

	return params, nil
}

func MP4ToTS(inputPath, outputPath string) error {
	// Build FFmpeg command with additional parameters to ensure SPS/PPS are included
	// and force the first frame to be an IDR frame
	cmd := exec.Command("ffmpeg",
		"-i", inputPath, // Input file
		"-c:v", "libx264", // Re-encode video to ensure proper frame order
		"-preset", "ultrafast", // Fast encoding
		"-tune", "zerolatency", // Low latency tuning
		"-x264-params", "keyint=30:min-keyint=30", // Force keyframes every 30 frames
		"-force_key_frames", "expr:gte(t,0)", // Force a keyframe at the start
		"-bsf:v", "h264_mp4toannexb", // Convert H.264 bitstream from MP4 to Annex B format
		"-avoid_negative_ts", "make_zero", // Avoid negative timestamps
		"-fflags", "+genpts", // Generate presentation timestamps
		"-f", "mpegts", // Output format
		"-y",       // Overwrite output file
		outputPath, // Output file
	)

	// Run the command
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("ffmpeg error: %v\nOutput: %s", err, string(output))
	}

	return nil
}

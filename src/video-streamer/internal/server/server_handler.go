package server

import (
	"log"
	"sync"

	"github.com/bluenviron/gortsplib/v4"
	"github.com/bluenviron/gortsplib/v4/pkg/base"
)

type ServerHandler struct {
	Server *gortsplib.Server
	Stream *gortsplib.ServerStream
	Mutex  sync.RWMutex
}

// called when a connection is opened.
func (sh *ServerHandler) OnConnOpen(_ *gortsplib.ServerHandlerOnConnOpenCtx) {
	log.Printf("conn opened")
}

// called when a connection is closed.
func (sh *ServerHandler) OnConnClose(ctx *gortsplib.ServerHandlerOnConnCloseCtx) {
	log.Printf("conn closed (%v)", ctx.Error)
}

// called when a session is opened.
func (sh *ServerHandler) OnSessionOpen(_ *gortsplib.ServerHandlerOnSessionOpenCtx) {
	log.Printf("session opened")
}

// called when a session is closed.
func (sh *ServerHandler) OnSessionClose(_ *gortsplib.ServerHandlerOnSessionCloseCtx) {
	log.Printf("session closed")
}

// called when receiving a DESCRIBE request.
func (sh *ServerHandler) OnDescribe(
	_ *gortsplib.ServerHandlerOnDescribeCtx,
) (*base.Response, *gortsplib.ServerStream, error) {
	log.Printf("DESCRIBE request")

	sh.Mutex.RLock()
	defer sh.Mutex.RUnlock()

	return &base.Response{
		StatusCode: base.StatusOK,
	}, sh.Stream, nil
}

// called when receiving a SETUP request.
func (sh *ServerHandler) OnSetup(
	_ *gortsplib.ServerHandlerOnSetupCtx,
) (*base.Response, *gortsplib.ServerStream, error) {
	log.Printf("SETUP request")

	sh.Mutex.RLock()
	defer sh.Mutex.RUnlock()

	return &base.Response{
		StatusCode: base.StatusOK,
	}, sh.Stream, nil
}

// called when receiving a PLAY request.
func (sh *ServerHandler) OnPlay(_ *gortsplib.ServerHandlerOnPlayCtx) (*base.Response, error) {
	log.Printf("PLAY request")

	return &base.Response{
		StatusCode: base.StatusOK,
	}, nil
}

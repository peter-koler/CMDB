package httpapi

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"

	"manager-go/internal/model"
	"manager-go/internal/notify"
	"manager-go/internal/store"
)

type Server struct {
	store    *store.MonitorStore
	notifier *notify.Service
	mux      *http.ServeMux
}

func NewServer(st *store.MonitorStore) *Server {
	s := &Server{store: st, notifier: notify.NewService(), mux: http.NewServeMux()}
	s.routes()
	return s
}

func (s *Server) Handler() http.Handler {
	return s.mux
}

func (s *Server) routes() {
	s.mux.HandleFunc("/api/v1/health", s.handleHealth)
	s.mux.HandleFunc("/api/v1/monitors", s.handleMonitors)
	s.mux.HandleFunc("/api/v1/monitors/", s.handleMonitorByID)
	s.mux.HandleFunc("/api/v1/notify/test", s.handleNotifyTest)
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "service": "manager-go"})
}

func (s *Server) handleMonitors(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		var in model.MonitorCreateInput
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
			return
		}
		m, err := s.store.Create(in)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		writeJSON(w, http.StatusCreated, m)
	case http.MethodGet:
		items := s.store.List()
		writeJSON(w, http.StatusOK, map[string]any{
			"items":     items,
			"page":      1,
			"page_size": len(items),
			"total":     len(items),
		})
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleMonitorByID(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/monitors/")
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		w.WriteHeader(http.StatusNotFound)
		return
	}
	id, err := strconv.ParseInt(parts[0], 10, 64)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "invalid monitor id")
		return
	}
	if len(parts) == 1 {
		s.handleMonitorCRUD(w, r, id)
		return
	}
	if len(parts) == 2 && r.Method == http.MethodPatch && (parts[1] == "enable" || parts[1] == "disable") {
		s.handleEnableDisable(w, r, id, parts[1] == "enable")
		return
	}
	w.WriteHeader(http.StatusNotFound)
}

func (s *Server) handleNotifyTest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	var req notify.TestSendRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	if err := s.notifier.TestSend(r.Context(), req); err != nil {
		writeErr(w, http.StatusBadRequest, "NOTIFY_SEND_FAILED", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (s *Server) handleMonitorCRUD(w http.ResponseWriter, r *http.Request, id int64) {
	switch r.Method {
	case http.MethodGet:
		m, err := s.store.Get(id)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, m)
	case http.MethodPut:
		var in model.MonitorUpdateInput
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
			return
		}
		m, err := s.store.Update(id, in)
		if err != nil {
			writeStoreErr(w, err)
			return
		}
		writeJSON(w, http.StatusOK, m)
	case http.MethodDelete:
		version, err := strconv.ParseInt(r.URL.Query().Get("version"), 10, 64)
		if err != nil || version <= 0 {
			writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", "version is required")
			return
		}
		if err := s.store.Delete(id, version); err != nil {
			writeStoreErr(w, err)
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

func (s *Server) handleEnableDisable(w http.ResponseWriter, r *http.Request, id int64, enabled bool) {
	var req struct {
		Version int64 `json:"version"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "INVALID_ARGUMENT", err.Error())
		return
	}
	m, err := s.store.SetEnabled(id, enabled, req.Version)
	if err != nil {
		writeStoreErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, m)
}

func writeStoreErr(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, store.ErrNotFound):
		writeErr(w, http.StatusNotFound, "MONITOR_NOT_FOUND", err.Error())
	case errors.Is(err, store.ErrVersionConflict):
		writeErr(w, http.StatusConflict, "MONITOR_CONFLICT", err.Error())
	case errors.Is(err, store.ErrInvalidInput):
		writeErr(w, http.StatusUnprocessableEntity, "MONITOR_INVALID_CONFIG", err.Error())
	default:
		writeErr(w, http.StatusInternalServerError, "INTERNAL_ERROR", err.Error())
	}
}

func writeErr(w http.ResponseWriter, status int, code string, msg string) {
	writeJSON(w, status, map[string]any{
		"error": map[string]any{
			"code":    code,
			"message": msg,
		},
	})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

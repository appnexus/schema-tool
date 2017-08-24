package server

import (
	"encoding/json"
	"net/http"
)

// createSchema is the JSON representation used to add a schema via the
// `newSchemaHandler`
type createSchema struct {
	Dir   string `json:"directory"`
	Empty bool   `json:"empty"`
}

// createdSchema is the JSON representation to return the ID of the created schema
type createdSchema struct {
	ID string `json:"id"`
}

// newSchemaHandler accepts a `createSchema` struct and scans the directory on the
// host the server is running on and creates an in-memory representation of the
// schema. This is then stored in-memory and an ID is returned to identify the
// schema for future operations.
//
// If the directory is not found, or the contents of the directory are not found
// to be a valid schema chain, then a 400 error response will be returned.
func (s *httpServer) newSchemaHandler(w http.ResponseWriter, r *http.Request) {
	create := &createSchema{}
	err := json.NewDecoder(r.Body).Decode(create)
	if err != nil {
		WriteErrorResponse(w, NewUserError(MalformedRequest, "Could not parse request body into expected JSON"))
		return
	}

	// check if directory exists
	// scan directory and build local representation
	// store in store and generate ID
	// return ID
}

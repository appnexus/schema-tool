// <--
// Copyright © 2017 AppNexus Inc.
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// -->

package log

/**
 * Define some simple logging infastrucutre that can be used from anywhere else in
 * the program. To use simply:
 *
 *    log.LEVEL.Println("my log message")
 *
 * Where LEVEL can be any one of:
 *    - Trace
 *    - Info
 *    - Warning
 *    - Error
 */

import (
	"io"
	"io/ioutil"
	"log"
	"os"
	"sync"
)

// Trace logger instance
var Trace *log.Logger

// Info logger instance
var Info *log.Logger

// Warn (ing) logger instance
var Warn *log.Logger

// Error logging instance
var Error *log.Logger

// simple object to ensure that we only run the InitLoggers function once
// even if called multiple times
var once sync.Once

// InitLoggers initializes loggers (varies based on whether or not we're "trace" logging)
func InitLoggers(traceLoggingEnabled bool) {
	shouldInit := false
	once.Do(func() { shouldInit = true })
	if !shouldInit {
		return
	}

	infoHandle := os.Stderr
	warningHandle := os.Stderr
	errorHandle := os.Stderr

	var traceHandle io.Writer
	var logFormat int

	if traceLoggingEnabled {
		traceHandle = os.Stderr
		logFormat = log.Ldate | log.Ltime | log.Lshortfile
	} else {
		traceHandle = ioutil.Discard
		logFormat = log.Ldate | log.Ltime
	}

	Trace = log.New(traceHandle, "TRACE: ", logFormat)
	Info = log.New(infoHandle, "INFO: ", logFormat)
	Warn = log.New(warningHandle, "WARNING: ", logFormat)
	Error = log.New(errorHandle, "ERROR: ", logFormat)
}

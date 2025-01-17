/*
 * Copyright (c) 2015 Roc Streaming authors
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

#include "roc_core/log.h"
#include "roc_core/panic.h"
#include "roc_core/stddefs.h"
#include "roc_core/thread.h"

namespace roc {
namespace core {

namespace {

void backend_handler(const LogMessage& msg, void** args) {
    roc_panic_if(!args);
    roc_panic_if(!args[0]);

    ((LogBackend*)args[0])->handle(msg);
}

} // namespace

Logger::Logger()
    : level_(LogError)
    , colors_mode_(ColorsDisabled)
    , location_mode_(LocationDisabled) {
    handler_ = &backend_handler;
    handler_args_[0] = &backend_;
}

void Logger::set_verbosity(unsigned verb) {
    switch (verb) {
    case 0:
        set_level(LogError);
        set_location(LocationDisabled);
        break;

    case 1:
        set_level(LogInfo);
        set_location(LocationDisabled);
        break;

    case 2:
        set_level(LogDebug);
        set_location(LocationDisabled);
        break;

    case 3:
        set_level(LogDebug);
        set_location(LocationEnabled);
        break;

    default:
        set_level(LogTrace);
        set_location(LocationEnabled);
        break;
    }
}

void Logger::set_level(LogLevel level) {
    Mutex::Lock lock(mutex_);

    if ((int)level < LogNone) {
        level = LogNone;
    }

    if ((int)level > LogTrace) {
        level = LogTrace;
    }

    AtomicOps::store_relaxed(level_, level);
}

void Logger::set_location(LocationMode mode) {
    Mutex::Lock lock(mutex_);

    location_mode_ = mode;
}

void Logger::set_colors(ColorsMode mode) {
    Mutex::Lock lock(mutex_);

    colors_mode_ = mode;
}

void Logger::set_handler(LogHandler handler, void** args, size_t n_args) {
    Mutex::Lock lock(mutex_);

    roc_panic_if(n_args > MaxArgs);
    roc_panic_if(!args && n_args);
    roc_panic_if(args && !n_args);

    if (handler) {
        handler_ = handler;
        memset(handler_args_, 0, sizeof(handler_args_));
        if (n_args) {
            memcpy(handler_args_, args, sizeof(void*) * n_args);
        }
    } else {
        handler_ = &backend_handler;
        handler_args_[0] = &backend_;
    }
}

void Logger::writef(LogLevel level,
                    const char* module,
                    const char* file,
                    int line,
                    const char* format,
                    ...) {
    Mutex::Lock lock(mutex_);

    if (level > level_ || level == LogNone) {
        return;
    }

    char message[256] = {};
    va_list args;
    va_start(args, format);
    if (vsnprintf(message, sizeof(message) - 1, format, args) < 0) {
        message[0] = '\0';
    }
    va_end(args);

    LogMessage msg;
    msg.level = level;
    msg.module = module;
    if (location_mode_ == LocationEnabled) {
        msg.file = file;
        msg.line = line;
    }
    msg.time = timestamp(ClockUnix);
    msg.pid = Thread::get_pid();
    msg.tid = Thread::get_tid();
    msg.message = message;
    msg.colors_mode = colors_mode_;

    handler_(msg, handler_args_);
}

} // namespace core
} // namespace roc

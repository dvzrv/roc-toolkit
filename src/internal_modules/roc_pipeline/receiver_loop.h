/*
 * Copyright (c) 2017 Roc Streaming authors
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

//! @file roc_pipeline/receiver_loop.h
//! @brief Receiver pipeline loop.

#ifndef ROC_PIPELINE_RECEIVER_LOOP_H_
#define ROC_PIPELINE_RECEIVER_LOOP_H_

#include "roc_core/buffer_factory.h"
#include "roc_core/iallocator.h"
#include "roc_core/mutex.h"
#include "roc_core/optional.h"
#include "roc_core/stddefs.h"
#include "roc_packet/packet_factory.h"
#include "roc_pipeline/config.h"
#include "roc_pipeline/pipeline_loop.h"
#include "roc_pipeline/receiver_source.h"
#include "roc_sndio/isource.h"

namespace roc {
namespace pipeline {

//! Receiver pipeline loop.
//!
//! This class acts as a task-based facade for the receiver pipeline subsystem
//! of roc_pipeline module (ReceiverSource, ReceiverSlot, ReceiverEndpoint,
//! ReceiverSessionGroup, ReceiverSession).
//!
//! It provides two interfaces:
//!
//!  - sndio::ISource - can be used to retrieve samples from the pipeline
//!    (should be used from sndio thread)
//!
//!  - PipelineLoop - can be used to schedule tasks on the pipeline
//!    (can be used from any thread)
//!
//! @note
//!  Private inheritance from ISource is used to decorate actual implementation
//!  of ISource - ReceiverSource, in order to integrate it with PipelineLoop.
class ReceiverLoop : public PipelineLoop, private sndio::ISource {
public:
    //! Opaque slot handle.
    typedef struct SlotHandle* SlotHandle;

    //! Base task class.
    class Task : public PipelineTask {
    protected:
        friend class ReceiverLoop;

        Task();

        bool (ReceiverLoop::*func_)(Task&); //!< Task implementation method.

        ReceiverSlot* slot_;       //!< Slot.
        address::Interface iface_; //!< Interface.
        address::Protocol proto_;  //!< Protocol.
        packet::IWriter* writer_;  //!< Packet writer.
    };

    //! Subclasses for specific tasks.
    class Tasks {
    public:
        //! Add new slot.
        class CreateSlot : public Task {
        public:
            //! Set task parameters.
            CreateSlot();

            //! Get created slot handle.
            SlotHandle get_handle() const;
        };

        //! Create endpoint on given interface of the slot.
        class CreateEndpoint : public Task {
        public:
            //! Set task parameters.
            //! @remarks
            //!  Each slot can have one source and zero or one repair endpoint.
            //!  The protocols of endpoints in one slot should be compatible.
            CreateEndpoint(SlotHandle slot,
                           address::Interface iface,
                           address::Protocol proto);

            //! Get packet writer for the endpoint.
            //! @remarks
            //!  The returned writer may be used from any thread.
            packet::IWriter* get_writer() const;
        };

        //! Delete endpoint on given interface of the slot, if it exists.
        class DeleteEndpoint : public Task {
        public:
            //! Set task parameters.
            DeleteEndpoint(SlotHandle slot, address::Interface iface);
        };
    };

    //! Initialize.
    ReceiverLoop(IPipelineTaskScheduler& scheduler,
                 const ReceiverConfig& config,
                 const rtp::FormatMap& format_map,
                 packet::PacketFactory& packet_factory,
                 core::BufferFactory<uint8_t>& byte_buffer_factory,
                 core::BufferFactory<audio::sample_t>& sample_buffer_factory,
                 core::IAllocator& allocator);

    //! Check if the pipeline was successfully constructed.
    bool valid() const;

    //! Get receiver sources.
    //! @remarks
    //!  Samples received from remote peers become available in this source.
    sndio::ISource& source();

private:
    // Methods of sndio::ISource
    virtual audio::SampleSpec sample_spec() const;
    virtual core::nanoseconds_t latency() const;
    virtual bool has_clock() const;
    virtual State state() const;
    virtual void pause();
    virtual bool resume();
    virtual bool restart();
    virtual void reclock(packet::ntp_timestamp_t timestamp);
    virtual bool read(audio::Frame&);

    // Methods of PipelineLoop
    virtual core::nanoseconds_t timestamp_imp() const;
    virtual bool process_subframe_imp(audio::Frame& frame);
    virtual bool process_task_imp(PipelineTask& task);

    // Methods for tasks
    bool task_create_slot_(Task& task);
    bool task_create_endpoint_(Task& task);
    bool task_delete_endpoint_(Task& task);

    ReceiverSource source_;

    core::Optional<core::Ticker> ticker_;
    packet::timestamp_t timestamp_;

    core::Mutex read_mutex_;

    bool valid_;
};

} // namespace pipeline
} // namespace roc

#endif // ROC_PIPELINE_RECEIVER_LOOP_H_

#pragma once

#include "presonus/avb/streams.hpp"

#include "core/public/corelinkedlist.h"
#include <array>
#include <cstdint>

namespace Presonus::AVB {
class AvbNoticeListener;
}

namespace presonus::avb {
// Independent boundary for original notice slots 0 and 1. No original notice
// interface declaration, return spelling or object layout is invented.
class NoticeSink {
public:
  virtual ~NoticeSink() = default;
  virtual std::uint32_t
  listenerChanged(Presonus::AVB::AvbNoticeListener *originalIdentity,
                  Presonus::AVB::AvbListener *stream) = 0;
  virtual std::uint32_t
  talkerChanged(Presonus::AVB::AvbNoticeListener *originalIdentity,
                Presonus::AVB::AvbTalker *stream) = 0;
};

struct ReceiveContext {
  ReceiveContext() = default;
  ReceiveContext(const ReceiveContext &) = delete;
  ReceiveContext &operator=(const ReceiveContext &) = delete;
  std::int32_t processingWord = 0;
  unsigned char command = 0;
  unsigned char status = 0;
  // Actual pinned CCL lists own their link nodes, never the borrowed streams.
  // Ordered non-null pointers; first matching ID wins. No old ARM ABI claim.
  Core::LinkedList<Presonus::AVB::AvbListener *> listeners;
  Core::LinkedList<Presonus::AVB::AvbTalker *> talkers;
  Presonus::AVB::AvbNoticeListener *noticeIdentity = nullptr;
  NoticeSink *notices = nullptr;
  // Explicit model for original preexisting frame bytes on truncated input.
  // Valid complete protocol fields do not depend on this seed. It is not a
  // recovered deterministic firmware behavior for indeterminate stack data.
  std::array<unsigned char, 64> initialScratch{};
  unsigned char prefixBeforeData = 0;
};
} // namespace presonus::avb

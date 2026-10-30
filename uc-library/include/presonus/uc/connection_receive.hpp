#pragma once
#include "core/public/corebuffer.h"
#include "core/system/corethread.h"
#include "presonus/uc/connection.hpp"
#include "presonus/uc/event_factory.hpp"

namespace presonus::uc {
struct ConnectionReceiveObserver {
  void *context = nullptr;
  void (*received)(void *, int, const Presonus::UC::Event &, int,
                   const char *) = nullptr;
};
// Independent existing-provider/state bridge. The buffer may be shared between
// connections to model original gEventBuffer storage; callers must serialize
// its use. No Core singleton/lock/container/socket implementation is supplied.
struct ConnectionReceiveState {
  unsigned char pending = 0;
  std::uint32_t magicBits = 0;
  unsigned short kindBits = 0, length = 0;
  Core::IO::Buffer *buffer = nullptr;
  int connectionIndex = 0;
  const char *connectionName = nullptr;
  std::uint64_t receivedBytes = 0, receivedEvents = 0;
  void *context = nullptr;
  bool (*readable)(void *, int) = nullptr;
  int (*available)(void *) = nullptr;
  int (*read)(void *, void *, int) = nullptr;
  Presonus::UC::EventFactory &(*factory)(void *) = nullptr;
  int observerCount = 0;
  const ConnectionReceiveObserver *observers = nullptr;
  void (*lock)(void *) = nullptr;
  void (*unlock)(void *) = nullptr;
  void (*append)(void *, Presonus::UC::EventItem *) = nullptr;
};
} // namespace presonus::uc

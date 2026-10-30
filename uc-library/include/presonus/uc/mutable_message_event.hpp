#pragma once
#include "core/public/corebuffer.h"
#include "presonus/uc/network_manager_services.hpp"

namespace Core::IO {
class MemoryStream;
}
namespace presonus::uc {
struct MutableMessageEventPortAccess;
}
namespace Presonus::UC {
class MessageAttributes;
// Independent common-prefix composition. Original inheritance, field types,
// ARM layout and any original non-exported destructor remain unresolved.
class MutableMessageEvent {
public:
  MutableMessageEvent();
  MutableMessageEvent(const MessageAttributes &, int type, int allocationHint);
  // Real Buffer lifetime cleanup is a source-port ownership requirement, not a
  // recovered standalone original destructor symbol.
  ~MutableMessageEvent() = default;
  MutableMessageEvent(const MutableMessageEvent &) = delete;
  MutableMessageEvent &operator=(const MutableMessageEvent &) = delete;
  MutableMessageEvent(MutableMessageEvent &&) = delete;
  MutableMessageEvent &operator=(MutableMessageEvent &&) = delete;
  // Original ordinary return spellings remain pending.
  MutableMessageEvent &assign(const MessageAttributes &, int type,
                              int allocationHint);
  MutableMessageEvent &assign(Core::IO::MemoryStream &, int type);
  void takeData(Core::IO::MemoryStream &, bool compress);

private:
  friend struct presonus::uc::MutableMessageEventPortAccess;
  MessageEvent event_{};
  Core::IO::Buffer buffer_;
};
} // namespace Presonus::UC
namespace presonus::uc {
// Independent observation/conversion API, not an original ELF method.
struct MutableMessageEventPortAccess {
  static const Presonus::UC::MessageEvent &
  event(const Presonus::UC::MutableMessageEvent &object) {
    return object.event_;
  }
  static const Core::IO::Buffer &
  buffer(const Presonus::UC::MutableMessageEvent &object) {
    return object.buffer_;
  }
};
} // namespace presonus::uc

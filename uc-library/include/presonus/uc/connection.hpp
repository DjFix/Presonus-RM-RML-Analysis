#pragma once
#include "presonus/uc/basic_connection.hpp"
#include "presonus/uc/events.hpp"
#include <array>
#include <cstddef>
#include <cstdint>

namespace presonus::uc {
struct ConnectionReceiveState;
// Independent bounded views; these are not recovered Core containers or
// original sender/object layouts. Entries and opaque identities must be live.
struct ConnectionSenderView {
  void *identity;
  std::uint32_t remoteBits;
  std::uint32_t localBits;
};
struct ConnectionReplyView {
  Presonus::UC::Event header;
  std::array<std::uint32_t, 2> payloadWords;
};
struct ConnectionState {
  const ConnectionSenderView *senders = nullptr;
  std::size_t senderCount = 0;
  std::uint32_t channelLimitBits = 0;
  void *context = nullptr;
  int (*granularity)(void *) = nullptr;
  std::array<std::uint32_t, 2> (*queryPayload)(
      void *, const Presonus::UC::Event &) = nullptr;
  // A synchronous callback must copy any needed reply contents before return;
  // the original constructs a temporary reply on its stack and ignores result.
  bool (*sendReply)(void *, const ConnectionReplyView &) = nullptr;
  ConnectionReceiveState *receive = nullptr;
};
} // namespace presonus::uc

namespace Presonus::UC {
// Original RTTI proves BasicConnection base. Constructors below are independent
// source-port borrowed-state APIs; no original lifecycle or ARM ABI claim.
class Connection : public BasicConnection {
public:
  Connection(presonus::uc::ConnectionState &state,
             presonus::uc::BasicConnectionState &outgoing)
      : BasicConnection(outgoing), state_(state) {}
  // Original pure slots follow inherited queue/send and virtual destruction.
  // Ordinary return spellings remain intentional source-port choices.
  virtual int getType() const = 0;
  virtual void getAddress(const char *&, unsigned short &) const = 0;
  // Original slot exists with concrete body, not yet recovered. Deliberate
  // source-port pure marker prevents silently fabricating process behavior.
  virtual bool process(bool) = 0;
  virtual bool reset();
  virtual void adjustRouting(Event &, bool);
  virtual bool handleInternal(const Event &);
  virtual bool sendPeriodicEvent(const Event &);
  void *findSender(int) const;
  void *findSenderWithLocalID(int) const;
  void initChannel();
  bool readEvents();

private:
  presonus::uc::ConnectionState &state_;
};
} // namespace Presonus::UC

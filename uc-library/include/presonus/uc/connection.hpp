#pragma once
#include "presonus/uc/basic_connection.hpp"
#include "presonus/uc/events.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>

namespace presonus::uc {
struct ConnectionReceiveState;
struct ConnectionSourceAccess;
struct ConnectionTransportProvider;
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
class ConnectionHandler;
class EventDispatcher;
class RemoteEventSender;

// Original RTTI establishes the BasicConnection base. The implementation uses
// portable source-provider state; original member offsets remain unresolved.
class Connection : public BasicConnection {
public:
  Connection(presonus::uc::ConnectionState &state,
             presonus::uc::BasicConnectionState &outgoing);
  Connection(ConnectionHandler &, int);
  ~Connection() override;

  // Local sender operations require owning construction and serialized use.
  // Return declarations are portable spellings of observed register results.
  RemoteEventSender *addSender(int);
  void removeSender(int);
  int makeLocalID(int);
  // Original pure slots follow inherited queue/send and virtual destruction.
  // Ordinary return spellings remain intentional source-port choices.
  virtual int getType() const = 0;
  virtual void getAddress(const char *&, unsigned short &) const = 0;
  // Reconstructed transport/lifecycle uses actual app and pinned CCL providers.
  // The bool return is a source-port health result; original spelling is
  // unknown.
  virtual bool process(bool);
  void dispatchReceived(EventItem *);
  struct ChannelWriter {
    IDataChannel &channel;
    unsigned char *data;
    int capacity;
    int position = 0;
  };
  bool writeEvent(ChannelWriter &, const Event &);
  bool writeEvents(bool);
  virtual bool reset();
  virtual void adjustRouting(Event &, bool);
  virtual bool handleInternal(const Event &);
  virtual bool sendPeriodicEvent(const Event &);
  void *findSender(int) const;
  void *findSenderWithLocalID(int) const;
  void initChannel();
  bool readEvents();

private:
  friend struct presonus::uc::ConnectionSourceAccess;
  struct SourceOwned;
  SourceOwned &requireOwned();
  bool handleOwnedInternal(const Event &);
  RemoteEventSender *findOwnedSender(int, bool byLocalID) const;
  std::unique_ptr<SourceOwned> owned_;
  presonus::uc::ConnectionState &state_;
};
} // namespace Presonus::UC

namespace presonus::uc {
// Independent provider access for application bindings and offline replays.
struct ConnectionSourceAccess {
  static Presonus::UC::ConnectionHandler &handler(Presonus::UC::Connection &);
  static Presonus::UC::EventDispatcher &dispatcher(Presonus::UC::Connection &);
  static Presonus::UC::EventQueue &incomingQueue(Presonus::UC::Connection &);
  static OwnedEventQueueState &incoming(Presonus::UC::Connection &);
  static ConnectionTransportProvider &transport(Presonus::UC::Connection &);
  static int senderCount(Presonus::UC::Connection &);
  static Presonus::UC::RemoteEventSender &senderAt(Presonus::UC::Connection &,
                                                   int);
};
} // namespace presonus::uc

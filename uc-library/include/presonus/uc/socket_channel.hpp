#pragma once
#include "core/public/corestringbuffer.h"
#include "presonus/uc/connection.hpp"
namespace presonus::uc {
// Independent existing-I/O-provider contract, not a CoreSocket definition.
// receive must return <=requested bytes or a negative error. Zero retries
// indefinitely in the original; a bounded caller/test must supply eventual
// progress or an error. Buffers must remain live and disjoint from state.
struct SocketConnectionState {
  Core::CStringBuffer<256> remoteAddress;
  unsigned short remotePort = 0;
};
struct SocketConnectionSourcePortTag {};
struct SocketChannelIO {
  void *context = nullptr;
  int (*receive)(void *, void *, int, int flags) = nullptr;
  int (*sendAll)(void *, const void *, int, int flags) = nullptr;
  bool (*readable)(void *, int) = nullptr;
  bool (*writable)(void *, int) = nullptr;
  bool (*error)(void *, int) = nullptr;
  int (*available)(void *, int &) = nullptr;
};
} // namespace presonus::uc
namespace Presonus::UC {
// Original single-inheritance RTTI and existing nested Channel scope retained.
// Independent source-state constructor, not an original lifecycle recovery.
class SocketConnection : public Connection {
public:
  SocketConnection(presonus::uc::SocketConnectionSourcePortTag,
                   presonus::uc::ConnectionState &state,
                   presonus::uc::BasicConnectionState &outgoing,
                   presonus::uc::SocketConnectionState &socket)
      : Connection(state, outgoing), socket_(socket) {}
  void getAddress(const char *&, unsigned short &) const override;
  // Original Socket overrides exist, but bodies remain unrecovered here.
  // Pure source-port markers avoid inherited base behavior masquerading as
  // recovered Socket behavior. Test adapters must never execute these paths.
  bool handleInternal(const Event &) override = 0;
  bool sendPeriodicEvent(const Event &) override = 0;
  class Channel {
  public:
    explicit Channel(presonus::uc::SocketChannelIO &io) : io_(io) {}
    // Virtualness and method order are proved by both original ELF vtables.
    virtual bool isReadable(int);
    virtual int getBytesAvailable();
    virtual int read(void *, int);
    virtual bool isWritable(int);
    virtual int getGranularity();
    virtual int write(const void *, int);
    virtual bool hasErrors(int);
    // Independent PORTABLE lifetime helper only. Original D1/D0 destructor
    // semantics, socket ownership, inheritance and ARM ABI are NOT recovered.
    virtual ~Channel() = default;

  private:
    presonus::uc::SocketChannelIO &io_;
  };

private:
  presonus::uc::SocketConnectionState &socket_;
};
} // namespace Presonus::UC

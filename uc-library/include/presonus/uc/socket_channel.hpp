#pragma once
#include "core/network/coresocket.h"
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
  unsigned short periodicPort = 0;
  Core::Sockets::IPAddress resolvedAddress;
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
  SocketConnection(ConnectionHandler &, int);
  ~SocketConnection() override;
  void getAddress(const char *&, unsigned short &) const override;
  // Original-named overrides use explicit typed app/CCL source providers.
  bool handleInternal(const Event &) override;
  bool sendPeriodicEvent(const Event &) override;
  class Channel : public IDataChannel {
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
    // Owning construction deletes the genuine CCL socket; borrowed I/O does
    // not acquire ownership. Original private layout/ARM ABI remain unknown.
    virtual ~Channel();
    // Independent owning provider constructor; legacy CoreSocket ABI absent.
    explicit Channel(std::unique_ptr<Core::Sockets::Socket>);
    Core::Sockets::Socket *sourceSocket() { return socket_.get(); }

  private:
    std::unique_ptr<Core::Sockets::Socket> socket_;
    presonus::uc::SocketChannelIO ownedIO_;
    presonus::uc::SocketChannelIO &io_;
  };

protected:
  presonus::uc::SocketConnectionState ownedSocketState_;
  presonus::uc::SocketConnectionState &socket_;
  std::unique_ptr<Channel> ownedChannel_;
};
} // namespace Presonus::UC

#pragma once
#include "core/network/coresocket.h"
#include "core/public/corebuffer.h"
#include "core/public/corehashmap.h"
#include "core/system/corethread.h"
#include "presonus/uc/connection_receive.hpp"
#include "presonus/uc/socket_channel.hpp"
#include <climits>
#include <optional>

namespace presonus::uc {
// Real pinned CCL public Socket, deliberately NOT an invented CoreSocket class
// or old Core symbol/ABI alias. The caller owns the genuine socket lifetime.
class CclSocketChannel {
public:
  explicit CclSocketChannel(Core::Sockets::Socket &socket);
  CclSocketChannel(const CclSocketChannel &) = delete;
  CclSocketChannel &operator=(const CclSocketChannel &) = delete;
  Presonus::UC::SocketConnection::Channel &channel() { return channel_; }

private:
  SocketChannelIO io_;
  Presonus::UC::SocketConnection::Channel channel_;
};

// Actual CCL HashMap storage. The existing independent FactoryRegistry bridge
// selects this backend; legacy std::map storage is unused in this mode.
class CclFactoryRegistry {
public:
  explicit CclFactoryRegistry(int modulus = 8);
  CclFactoryRegistry(const CclFactoryRegistry &) = delete;
  CclFactoryRegistry &operator=(const CclFactoryRegistry &) = delete;
  FactoryRegistry &registry() { return bridge_; }
  bool remove(int type) { return entries_.remove(type); }

private:
  static int hash(const int &, int);
  Core::HashMap<int, const FactoryCodec *> entries_;
  FactoryRegistry bridge_;
};

// A NEW holder usable with actual CCL StaticSingleton. This is not an original
// EventFactory default constructor or original pooled class registration.
struct CclFactoryHolder {
  CclFactoryRegistry registrations;
  Presonus::UC::EventFactory factory;
  CclFactoryHolder() : registrations(8), factory(registrations.registry()) {}
};
CclFactoryHolder &cclFactoryHolder();

// Views over actual CCL Buffer storage, not copies or replacement Core types.
// A returned view must not outlive this adapter/storage or any storage resize.
class CclBufferViews {
public:
  explicit CclBufferViews(Core::IO::Buffer &storage) : storage_(storage) {}
  CclBufferViews(const CclBufferViews &) = delete;
  CclBufferViews &operator=(const CclBufferViews &) = delete;
  std::optional<Presonus::UC::BufferReader> reader(Core::uint32 length,
                                                   Core::uint32 cursor = 0);
  std::optional<Presonus::UC::BufferWriter> writer(Core::uint32 length,
                                                   Core::uint32 cursor = 0);

private:
  void *address(Core::uint32 length, Core::uint32 cursor);
  Core::IO::Buffer &storage_;
  unsigned char empty_ = 0;
};

// Borrowed actual CCL socket/lock/buffer, with caller-owned application event
// observers and receive-queue append. No Core body or class is synthesized.
class CclReceiveProviders {
public:
  CclReceiveProviders(CclSocketChannel &socket, Core::Threads::Lock &lock,
                      Presonus::UC::EventFactory &factory, void *appendContext,
                      void (*append)(void *, Presonus::UC::EventItem *));
  CclReceiveProviders(const CclReceiveProviders &) = delete;
  CclReceiveProviders &operator=(const CclReceiveProviders &) = delete;
  bool bind(ConnectionReceiveState &, Core::IO::Buffer &);

private:
  CclSocketChannel &socket_;
  Core::Threads::Lock &lock_;
  Presonus::UC::EventFactory &factory_;
  void *appendContext_;
  void (*append_)(void *, Presonus::UC::EventItem *);
};
} // namespace presonus::uc

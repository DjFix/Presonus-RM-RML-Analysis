#include "presonus/uc/ccl_bindings.hpp"
#include "core/portable/coresingleton.h"
#include <stdexcept>

// This is the unmodified official CCL extension macro for a NEW independent
// holder type; no old Core ELF singleton body/symbol is reconstructed.
DEFINE_STATIC_SINGLETON(presonus::uc::CclFactoryHolder)

namespace presonus::uc {
namespace {
int positiveModulus(int value) {
  if (value <= 0)
    throw std::invalid_argument("positive CCL hash modulus required");
  return value;
}
} // namespace
CclSocketChannel::CclSocketChannel(Core::Sockets::Socket &socket)
    : io_{&socket,
          [](void *p, void *b, int n, int f) {
            return static_cast<Core::Sockets::Socket *>(p)->receive(b, n, f);
          },
          [](void *p, const void *b, int n, int f) {
            return static_cast<Core::Sockets::Socket *>(p)->sendAll(b, n, f);
          },
          [](void *p, int n) {
            return static_cast<Core::Sockets::Socket *>(p)->isReadable(n);
          },
          [](void *p, int n) {
            return static_cast<Core::Sockets::Socket *>(p)->isWritable(n);
          },
          [](void *p, int n) {
            return static_cast<Core::Sockets::Socket *>(p)->isAnyError(n);
          },
          [](void *p, int &n) {
            return static_cast<Core::Sockets::Socket *>(p)->getBytesAvailable(
                n);
          }},
      channel_(io_) {}
int CclFactoryRegistry::hash(const int &key, int modulus) {
  const int raw = Presonus::UC::EventFactory::hashEventType(key, modulus);
  // The original signed hash result remains unchanged at its UC API. Adapt
  // only the index consumed by actual CCL's nonnegative table storage.
  return raw < 0 ? raw + modulus : raw;
}
CclFactoryRegistry::CclFactoryRegistry(int modulus)
    : entries_(positiveModulus(modulus), hash, nullptr) {
  bridge_.modulus = modulus;
  bridge_.sourceBackendContext = this;
  bridge_.sourceBackendGet = [](void *p, const FactoryCodec *&out, int key) {
    return static_cast<CclFactoryRegistry *>(p)->entries_.get(out, key);
  };
  bridge_.sourceBackendAppend = [](void *p, int key,
                                   const FactoryCodec *value) {
    static_cast<CclFactoryRegistry *>(p)->entries_.add(key, value);
  };
}
CclFactoryHolder &cclFactoryHolder() {
  return Core::Portable::StaticSingleton<CclFactoryHolder>::instance();
}
void *CclBufferViews::address(Core::uint32 length, Core::uint32 cursor) {
  if (length > storage_.getSize() || length > INT_MAX || cursor > length)
    return nullptr;
  void *p = storage_.getAddress();
  if (!p && length)
    return nullptr;
  // Empty-buffer backing must still be a valid pointer for the recovered UC
  // constructors' pointer arithmetic; no invalid cursor is normalized.
  return p ? p : &empty_;
}
std::optional<Presonus::UC::BufferReader>
CclBufferViews::reader(Core::uint32 length, Core::uint32 cursor) {
  void *p = address(length, cursor);
  if (!p)
    return std::nullopt;
  return Presonus::UC::BufferReader(p, int(length), int(cursor));
}
std::optional<Presonus::UC::BufferWriter>
CclBufferViews::writer(Core::uint32 length, Core::uint32 cursor) {
  void *p = address(length, cursor);
  if (!p)
    return std::nullopt;
  return Presonus::UC::BufferWriter(p, int(length), int(cursor));
}
CclReceiveProviders::CclReceiveProviders(
    CclSocketChannel &s, Core::Threads::Lock &l, Presonus::UC::EventFactory &f,
    void *c, void (*a)(void *, Presonus::UC::EventItem *))
    : socket_(s), lock_(l), factory_(f), appendContext_(c), append_(a) {}
bool CclReceiveProviders::bind(ConnectionReceiveState &state,
                               Core::IO::Buffer &storage) {
  if (storage.getSize() < 16390 || !storage.getAddress() || !append_)
    return false;
  state.buffer = &storage;
  state.context = this;
  state.readable = [](void *p, int t) {
    return static_cast<CclReceiveProviders *>(p)->socket_.channel().isReadable(
        t);
  };
  state.available = [](void *p) {
    return static_cast<CclReceiveProviders *>(p)
        ->socket_.channel()
        .getBytesAvailable();
  };
  state.read = [](void *p, void *b, int n) {
    return static_cast<CclReceiveProviders *>(p)->socket_.channel().read(b, n);
  };
  state.factory = [](void *p) -> Presonus::UC::EventFactory & {
    return static_cast<CclReceiveProviders *>(p)->factory_;
  };
  state.lock = [](void *p) {
    static_cast<CclReceiveProviders *>(p)->lock_.lock();
  };
  state.unlock = [](void *p) {
    static_cast<CclReceiveProviders *>(p)->lock_.unlock();
  };
  state.append = [](void *p, Presonus::UC::EventItem *i) {
    auto &self = *static_cast<CclReceiveProviders *>(p);
    self.append_(self.appendContext_, i);
  };
  return true;
}
} // namespace presonus::uc

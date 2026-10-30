#pragma once
#include "core/public/corehashmap.h"
#include "presonus/uc/misc_events.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <memory>
#include <variant>
namespace Presonus::UC {
// Independent nonowning view; original LoopbackReplyEvent fields/layout
// unknown.
struct LoopbackReplyEvent {
  const Event &header;
};
} // namespace Presonus::UC
namespace presonus::uc {
// Serialized typed-reference provenance only. Referents have stable addresses
// and outlive bindings/callbacks. No concurrent mutation/destruction. This is
// app-owned source-port infrastructure, not an original ELF interface.
class ClientTypedOrigins {
public:
  using Payload = std::variant<
      const Presonus::UC::TimeCodeEvent *, const Presonus::UC::MessageEvent *,
      const Presonus::UC::BinaryEvent *, const Presonus::UC::DebugEvent *>;

private:
  struct Record {
    Payload payload;
    std::uint32_t tag;
    std::uint64_t serial;
    bool operator==(const Record &r) const {
      return payload == r.payload && tag == r.tag && serial == r.serial;
    }
  };
  struct State {
    static int hash(const Presonus::UC::Event *const &key, int size) {
      return int((reinterpret_cast<std::uintptr_t>(key) >> 3) %
                 std::uintptr_t(size));
    }
    Core::HashMap<const Presonus::UC::Event *, Record> records{32, hash};
    std::uint64_t next = 0;
  };

public:
  class Binding {
    friend class ClientTypedOrigins;
    std::weak_ptr<State> state_;
    const Presonus::UC::Event *header_ = nullptr;
    std::uint64_t serial_ = 0;
    Binding(std::shared_ptr<State> s, const Presonus::UC::Event *h,
            std::uint64_t n)
        : state_(s), header_(h), serial_(n) {}

  public:
    Binding() = default;
    Binding(const Binding &) = delete;
    Binding &operator=(const Binding &) = delete;
    Binding(Binding &&) noexcept;
    Binding &operator=(Binding &&) noexcept;
    ~Binding();
    void reset();
    explicit operator bool() const;
  };
  ClientTypedOrigins() : state_(std::make_shared<State>()) {}
  ClientTypedOrigins(const ClientTypedOrigins &) = delete;
  ClientTypedOrigins &operator=(const ClientTypedOrigins &) = delete;
  Binding bind(const Presonus::UC::TimeCodeEvent &);
  Binding bind(const Presonus::UC::MessageEvent &);
  Binding bind(const Presonus::UC::BinaryEvent &);
  Binding bind(const Presonus::UC::DebugEvent &);
  template <class T> const T *get(const Presonus::UC::Event *header) const {
    Record r;
    if (!header || !state_->records.get(r, header))
      return nullptr;
    if (header->type != r.tag)
      return nullptr;
    const auto *value = std::get_if<const T *>(&r.payload);
    return value ? *value : nullptr;
  }

private:
  std::shared_ptr<State> state_;
  Binding bindRaw(const Presonus::UC::Event &, Payload);
};
} // namespace presonus::uc

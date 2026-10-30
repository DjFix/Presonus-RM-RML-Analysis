#pragma once
#include "presonus/uc/meter_events.hpp"
#include "presonus/uc/parameter_events.hpp"
#include <memory>
#include <optional>
#include <variant>
namespace presonus::uc {
using ParamPayload = std::variant<const Presonus::UC::ParamValueEvent *,
                                  const Presonus::UC::ParamStringEvent *,
                                  const Presonus::UC::ParamColorEvent *,
                                  const Presonus::UC::ParamRangeEvent *,
                                  const Presonus::UC::ParamStringListEvent *>;
using MeterPayload = std::variant<const Presonus::UC::MeterEvent8 *,
                                  const Presonus::UC::MeterEvent16 *>;
} // namespace presonus::uc
namespace Presonus::UC {
// Source-native nonowning views bearing the original callback parameter names.
// Original field declarations, inheritance, constructors, size and ABI remain
// unknown. Every reference/pointer aliases a proven live source-owned value;
// views must not outlive that value or its origin binding. Payloads are not
// copied.
struct ParamEvent {
  const Event &header;
  const std::array<char, 128> &path;
  const unsigned short &index;
  presonus::uc::ParamPayload payload;
};
struct MeterEvent {
  const Event &header;
  const std::uint32_t &keyBits;
  const unsigned short &source, &count;
  const unsigned char &recordCount, &reserved25;
  const std::array<MeterRecord, 36> &records;
  const unsigned char *data;
  std::size_t dataCapacity;
  unsigned sampleWidth;
  presonus::uc::MeterPayload payload;
};
} // namespace Presonus::UC
namespace presonus::uc {
// Serialized access only: registries/factories/current codec bindings are not
// thread-safe. No concurrent payload mutation/destruction while views are used.
// Manual bindings require the actual typed value at a stable address to outlive
// binding and views. Concrete provenance tracker. A tag is never sufficient to
// recover a payload. Bindings originate from typed references or RTTI-checked
// actual TypedEventItem.
class EventOrigins {
  struct State;

public:
  enum class Kind {
    None,
    Value,
    String,
    Color,
    Range,
    StringList,
    Meter8,
    Meter16
  };
  class Binding {
  public:
    Binding() = default;
    Binding(const Binding &) = delete;
    Binding &operator=(const Binding &) = delete;
    Binding(Binding &&) noexcept;
    Binding &operator=(Binding &&) noexcept;
    ~Binding();
    void reset();
    explicit operator bool() const;

  private:
    friend class EventOrigins;
    Binding(std::weak_ptr<State>, const Presonus::UC::Event *, std::uint64_t);
    std::weak_ptr<State> state_;
    const Presonus::UC::Event *header_ = nullptr;
    std::uint64_t serial_ = 0;
  };
  EventOrigins();
  EventOrigins(const EventOrigins &) = delete;
  EventOrigins &operator=(const EventOrigins &) = delete;
  Binding bind(const Presonus::UC::ParamValueEvent &);
  Binding bind(const Presonus::UC::ParamStringEvent &);
  Binding bind(const Presonus::UC::ParamColorEvent &);
  Binding bind(const Presonus::UC::ParamRangeEvent &);
  Binding bind(const Presonus::UC::ParamStringListEvent &);
  Binding bind(const Presonus::UC::MeterEvent8 &);
  Binding bind(const Presonus::UC::MeterEvent16 &);
  Binding bindItem(Presonus::UC::EventItem &);
  std::optional<Presonus::UC::ParamEvent>
  param(const Presonus::UC::Event *) const;
  std::optional<Presonus::UC::MeterEvent>
  meter(const Presonus::UC::Event *) const;
  const void *typed(const Presonus::UC::Event *, Kind) const;
  int count() const;

private:
  Binding bindRaw(const Presonus::UC::Event *, const void *, Kind,
                  std::uint32_t);
  std::shared_ptr<State> state_;
};
// Complete factory/codec set using actual CCL-backed registry, EventFactory and
// TypedFactoryCodec wire bodies. Created/read items carry automatic origin
// cleanup even when deleted directly via EventItem*. Items may outlive factory;
// their weak binding then expires without accessing a dead registry.
class EventValueFactory {
public:
  using Item = std::unique_ptr<Presonus::UC::EventItem>;
  EventValueFactory();
  ~EventValueFactory();
  EventValueFactory(const EventValueFactory &) = delete;
  EventValueFactory &operator=(const EventValueFactory &) = delete;
  EventOrigins &origins();
  Presonus::UC::EventFactory &factory();
  Item createType(int);
  Item clone(const Presonus::UC::Event &);
  Item read(const char *, int);
  // Returns -1 for missing/mismatched provenance. For valid origins this
  // retains the actual factory's write-result/cursor semantics.
  int write(char *, int, const Presonus::UC::Event &);

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
} // namespace presonus::uc

#pragma once
#include "presonus/uc/typed_factory_codec.hpp"
namespace Presonus::UC {
// Portable field containers. Original field names, inheritance, constructors,
// layout/vtable ABI and numeric semantic types are unproved. Common observed
// storage is header+16, path128, indexLE16 at+144; numeric payloads preserve
// raw bits, including any NaN payloads. All strings are arbitrary byte strings.
struct ParamEditEvent {
  Event header;
  std::array<char, 128> path{};
  unsigned short index = 0;
};
struct ParamModeEvent {
  Event header;
  std::array<char, 128> path{};
  unsigned short index = 0;
  std::array<char, 64> modeBytes{};
};
struct ParamIncrementEvent {
  Event header;
  std::array<char, 128> path{};
  unsigned short index = 0, incrementBits = 0;
};
struct ParamColorEvent {
  Event header;
  std::array<char, 128> path{};
  unsigned short index = 0;
  std::array<unsigned char, 2> reserved92{};
  std::uint32_t colorBits = 0;
};
struct ParamRangeEvent {
  Event header;
  std::array<char, 128> path{};
  unsigned short index = 0;
  std::array<unsigned char, 2> reserved92{};
  std::array<std::uint32_t, 5> wordBits{};
  std::array<std::array<char, 32>, 2> labels{};
};
struct ParamStringListEvent {
  Event header;
  std::array<char, 128> path{};
  unsigned short index = 0;
  std::array<unsigned char, 2> reserved92{};
  std::uint32_t listFieldBits = 0;
  std::array<char, 1024> text{};
};
// Payload-only methods: stop at first failure, retaining every earlier field,
// output byte and cursor mutation. Non-template bool return spelling is a
// portable declaration matching ARM0/1; original spelling is unencoded.
class ParamEditEventClass {
public:
  bool write(BufferWriter &, const ParamEditEvent &) const;
  bool read(ParamEditEvent &, BufferReader &) const;
};
class ParamModeEventClass {
public:
  bool write(BufferWriter &, const ParamModeEvent &) const;
  bool read(ParamModeEvent &, BufferReader &) const;
};
class ParamIncrementEventClass {
public:
  bool write(BufferWriter &, const ParamIncrementEvent &) const;
  bool read(ParamIncrementEvent &, BufferReader &) const;
};
class ParamColorEventClass {
public:
  bool write(BufferWriter &, const ParamColorEvent &) const;
  bool read(ParamColorEvent &, BufferReader &) const;
};
class ParamRangeEventClass {
public:
  bool write(BufferWriter &, const ParamRangeEvent &) const;
  bool read(ParamRangeEvent &, BufferReader &) const;
};
class ParamStringListEventClass {
public:
  bool write(BufferWriter &, const ParamStringListEvent &) const;
  bool read(ParamStringListEvent &, BufferReader &) const;
};
template <>
bool PrimitiveEventClass<ParamEditEvent, 20549>::write(BufferWriter &,
                                                       const Event &) const;
template <>
bool PrimitiveEventClass<ParamEditEvent, 20549>::read(Event &,
                                                      BufferReader &) const;
template <>
bool PrimitiveEventClass<ParamModeEvent, 20557>::write(BufferWriter &,
                                                       const Event &) const;
template <>
bool PrimitiveEventClass<ParamModeEvent, 20557>::read(Event &,
                                                      BufferReader &) const;
template <>
bool PrimitiveEventClass<ParamIncrementEvent, 20553>::write(
    BufferWriter &, const Event &) const;
template <>
bool PrimitiveEventClass<ParamIncrementEvent, 20553>::read(
    Event &, BufferReader &) const;
template <>
bool PrimitiveEventClass<ParamColorEvent, 20547>::write(BufferWriter &,
                                                        const Event &) const;
template <>
bool PrimitiveEventClass<ParamColorEvent, 20547>::read(Event &,
                                                       BufferReader &) const;
template <>
bool PrimitiveEventClass<ParamRangeEvent, 20562>::write(BufferWriter &,
                                                        const Event &) const;
template <>
bool PrimitiveEventClass<ParamRangeEvent, 20562>::read(Event &,
                                                       BufferReader &) const;
template <>
bool PrimitiveEventClass<ParamStringListEvent, 20556>::write(
    BufferWriter &, const Event &) const;
template <>
bool PrimitiveEventClass<ParamStringListEvent, 20556>::read(
    Event &, BufferReader &) const;
} // namespace Presonus::UC
namespace presonus::uc {
using ParamEditFactoryCodec =
    TypedFactoryCodec<Presonus::UC::ParamEditEvent,
                      Presonus::UC::ParamEditEventClass, 20549>;
using ParamModeFactoryCodec =
    TypedFactoryCodec<Presonus::UC::ParamModeEvent,
                      Presonus::UC::ParamModeEventClass, 20557>;
using ParamIncrementFactoryCodec =
    TypedFactoryCodec<Presonus::UC::ParamIncrementEvent,
                      Presonus::UC::ParamIncrementEventClass, 20553>;
using ParamColorFactoryCodec =
    TypedFactoryCodec<Presonus::UC::ParamColorEvent,
                      Presonus::UC::ParamColorEventClass, 20547>;
using ParamRangeFactoryCodec =
    TypedFactoryCodec<Presonus::UC::ParamRangeEvent,
                      Presonus::UC::ParamRangeEventClass, 20562>;
using ParamStringListFactoryCodec =
    TypedFactoryCodec<Presonus::UC::ParamStringListEvent,
                      Presonus::UC::ParamStringListEventClass, 20556>;
} // namespace presonus::uc

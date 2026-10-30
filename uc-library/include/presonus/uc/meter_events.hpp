#pragma once
#include "presonus/uc/typed_factory_codec.hpp"
namespace Presonus::UC {
// Portable bounded storage, not an original object ABI declaration. Observed
// fields: BE32 key at +16, LE16 source/count at +20/+22, record-count byte +24,
// padding +25, 36 three-word records at +26, raw sample bytes at +242.
struct MeterRecord {
  unsigned short a = 0, b = 0, c = 0;
};
struct MeterEvent8 {
  static constexpr int sampleWidth = 1;
  Event header;
  std::uint32_t keyBits = 0;
  unsigned short source = 0, count = 0;
  unsigned char recordCount = 0, reserved25 = 0;
  std::array<MeterRecord, 36> records{};
  std::array<unsigned char, 1024> data{};
};
struct MeterEvent16 {
  static constexpr int sampleWidth = 2;
  Event header;
  std::uint32_t keyBits = 0;
  unsigned short source = 0, count = 0;
  unsigned char recordCount = 0, reserved25 = 0;
  std::array<MeterRecord, 36> records{};
  // Raw bytes are preserved; no float/level conversion or word normalization.
  std::array<unsigned char, 2048> data{};
};
template <class T, int Type> class MeterEventClass {
public:
  // Writer does not clamp either count. If the data copy succeeds, count must
  // fit bounded storage and recordCount must be <=36. Larger original writer
  // accesses are potentially unsafe and are outside this portable contract.
  // Reader copies min(byteCount,capacity) then skips excess, retaining partial
  // mutations on failure; it clamps retained/read recordCount to36. Several
  // header/tail read/write failures intentionally do not make the call fail.
  // Original non-template return spelling is unencoded; bool matches 0/1.
  bool write(BufferWriter &, const T &) const;
  bool read(T &, BufferReader &) const;
};
extern template class MeterEventClass<MeterEvent8, 19778>;
extern template class MeterEventClass<MeterEvent16, 19795>;
template <>
bool PrimitiveEventClass<MeterEvent8, 19778>::write(BufferWriter &,
                                                    const Event &) const;
template <>
bool PrimitiveEventClass<MeterEvent8, 19778>::read(Event &,
                                                   BufferReader &) const;
template <>
bool PrimitiveEventClass<MeterEvent16, 19795>::write(BufferWriter &,
                                                     const Event &) const;
template <>
bool PrimitiveEventClass<MeterEvent16, 19795>::read(Event &,
                                                    BufferReader &) const;
} // namespace Presonus::UC
namespace presonus::uc {
using Meter8FactoryCodec = TypedFactoryCodec<
    Presonus::UC::MeterEvent8,
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8, 19778>, 19778>;
using Meter16FactoryCodec = TypedFactoryCodec<
    Presonus::UC::MeterEvent16,
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16, 19795>, 19795>;
} // namespace presonus::uc

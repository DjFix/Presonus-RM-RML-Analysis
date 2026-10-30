#pragma once
#include "presonus/uc/typed_factory_codec.hpp"
namespace Presonus::UC {
// Portable storage only; original field names/semantic types, inheritance,
// constructors/layout/vtable ABI remain unproved. idBits is observed as32-bit
// storage at+16 but only its lowLE16 is serialized; read zero-extends or clears
// the entire stored word even on an insufficient-input failure.
struct FileRequestEvent {
  Event header;
  std::uint32_t idBits = 0, requestBits = 0;
  std::array<std::array<char, 256>, 2> strings{};
};
struct FileDataRateEvent {
  Event header;
  std::uint32_t idBits = 0;
  std::array<std::uint32_t, 3> wordBits{};
};
struct FileAbortEvent {
  Event header;
  std::uint32_t idBits = 0;
};
// Wire codecs only: no file/device/programming IO is executed. Request has
// BE32 at+20 then two arbitrary byte CStrings256 at+24/+280. DataRate has three
// rawLE32 words at+20/+24/+28. Sequential failures preserve prior mutations.
// Original non-template return spelling is unencoded; bool matches observed0/1.
class FileRequestEventClass {
public:
  bool write(BufferWriter &, const FileRequestEvent &) const;
  bool read(FileRequestEvent &, BufferReader &) const;
};
class FileDataRateEventClass {
public:
  bool write(BufferWriter &, const FileDataRateEvent &) const;
  bool read(FileDataRateEvent &, BufferReader &) const;
};
class FileAbortEventClass {
public:
  bool write(BufferWriter &, const FileAbortEvent &) const;
  bool read(FileAbortEvent &, BufferReader &) const;
};
template <>
bool PrimitiveEventClass<FileRequestEvent, 18002>::write(BufferWriter &,
                                                         const Event &) const;
template <>
bool PrimitiveEventClass<FileRequestEvent, 18002>::read(Event &,
                                                        BufferReader &) const;
template <>
bool PrimitiveEventClass<FileDataRateEvent, 18003>::write(BufferWriter &,
                                                          const Event &) const;
template <>
bool PrimitiveEventClass<FileDataRateEvent, 18003>::read(Event &,
                                                         BufferReader &) const;
template <>
bool PrimitiveEventClass<FileAbortEvent, 17985>::write(BufferWriter &,
                                                       const Event &) const;
template <>
bool PrimitiveEventClass<FileAbortEvent, 17985>::read(Event &,
                                                      BufferReader &) const;
} // namespace Presonus::UC
namespace presonus::uc {
using FileRequestFactoryCodec =
    TypedFactoryCodec<Presonus::UC::FileRequestEvent,
                      Presonus::UC::FileRequestEventClass, 18002>;
using FileDataRateFactoryCodec =
    TypedFactoryCodec<Presonus::UC::FileDataRateEvent,
                      Presonus::UC::FileDataRateEventClass, 18003>;
using FileAbortFactoryCodec =
    TypedFactoryCodec<Presonus::UC::FileAbortEvent,
                      Presonus::UC::FileAbortEventClass, 17985>;
} // namespace presonus::uc

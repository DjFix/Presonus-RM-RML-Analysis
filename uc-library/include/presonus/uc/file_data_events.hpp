#pragma once
#include "presonus/uc/typed_factory_codec.hpp"
namespace Presonus::UC {
// Portable fixed storage: originalnames/semantictypes/inheritance/constructors,
// ownership/layout/vtable/ARM ABI remain unproved. Observed +16 full32 ID with
// lowLE16 wirevalue, rawLE32 words+20/+24, LE16+28/count+30, data4096+32.
struct FileDataEvent {
  Event header;
  std::uint32_t idBits = 0;
  std::array<std::uint32_t, 2> wordBits{};
  unsigned short partBits = 0, count = 0;
  std::array<unsigned char, 4096> data{};
};
class FileDataEventClass {
public:
  // Sequential transfers preserve earlier output/cursor/field mutations. An
  // insufficient first ID read clears its entire32-bit field. Reader copies
  // min(count,4096) then skips excess, retaining full count and copied prefix
  // on failed skip. No Core buffer/allocator or file/device IO is involved.
  // Writer count is NOT clamped: >4096 is allowed only if capacity rejects
  // before data access; successful oversized original copies are unsafe.
  // Original non-template return spelling unencoded; bool matches ARM0/1.
  bool write(BufferWriter &, const FileDataEvent &) const;
  bool read(FileDataEvent &, BufferReader &) const;
};
template <>
bool PrimitiveEventClass<FileDataEvent, 17988>::write(BufferWriter &,
                                                      const Event &) const;
template <>
bool PrimitiveEventClass<FileDataEvent, 17988>::read(Event &,
                                                     BufferReader &) const;
} // namespace Presonus::UC
namespace presonus::uc {
using FileDataFactoryCodec =
    TypedFactoryCodec<Presonus::UC::FileDataEvent,
                      Presonus::UC::FileDataEventClass, 17988>;
}

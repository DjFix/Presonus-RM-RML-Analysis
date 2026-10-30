#pragma once
#include "core/portable/coreattributes.h"
#include <array>

namespace presonus::uc {
struct MessageAttributesPortAccess;
}
namespace Presonus::UC {
struct MessageEvent;
// Genuine original RTTI base, bound to actual pinned CCL source. Native source
// uses -fno-rtti because the installed CCL provider omits Core typeinfo;
// original RTTI/vtables are evidence, not a native or ARM32 ABI compatibility
// claim.
class MessageAttributes : public Core::Portable::Attributes {
public:
  explicit MessageAttributes(const char *id);
  explicit MessageAttributes(const MessageEvent &event);
  ~MessageAttributes() override;
  // Return pointer spelling/const qualification is a source-port choice; the
  // original ordinary return declarations remain unresolved.
  const char *getSource() const;
  const char *getURL() const;
  const char *getID() const;
  void setSource(const char *value);
  void setURL(const char *value);
  void setID(const char *value);
  // Source-port reference return; original ordinary declaration unresolved.
  MessageAttributes &assign(const MessageEvent &event);

private:
  friend struct presonus::uc::MessageAttributesPortAccess;
  // Original app writes two zero words at ARM offsets0x20/0x24. Their field
  // types remain unresolved; this independent8byte storage makes no oldlayout
  // claim. MessageEvent constructors/assign are outside this selected batch.
  std::array<unsigned char, 8> opaqueAppState_{};
};
} // namespace Presonus::UC
namespace presonus::uc {
// Explicitly independent source-port observation; not an original ELF method.
struct MessageAttributesPortAccess {
  static auto opaqueState(const Presonus::UC::MessageAttributes &object) {
    return object.opaqueAppState_;
  }
};
} // namespace presonus::uc

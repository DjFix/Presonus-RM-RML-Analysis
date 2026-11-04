#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::UC {
// Intentional source port: actual pinned CCL base, not original ARM layout.
class ServerComponent : public Core::Portable::Component {
public:
  using Core::Portable::Component::Component;
  ~ServerComponent() override;
};
} // namespace Presonus::UC
namespace presonus::avb {
// Explicit external AVB resource boundary; native slot +0x10 is observed.
class ComponentResource {
public:
  virtual ~ComponentResource() = default;
  virtual void release() = 0;
};
} // namespace presonus::avb

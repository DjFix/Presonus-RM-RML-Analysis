#pragma once
#include "core/public/corestringbuffer.h"
namespace Core::Portable {
class Parameter;
}
namespace Presonus::Mixer {
// Portable source state: original vtable, layout and ownership are unresolved.
class ControlMapping {
public:
  ControlMapping(Core::Portable::Parameter *, const char *);
  const char *name() const { return name_.str(); }
  Core::Portable::Parameter *parameter() const { return parameter_; }

private:
  Core::CString32 name_;
  Core::Portable::Parameter
      *parameter_; // borrowed; constructor does not retain
};
} // namespace Presonus::Mixer

#pragma once

#include "core/public/corevector.h"

namespace Core::Portable {
class ComponentDescriptor;
}

namespace Presonus {

class MixerClassManager {
public:
  MixerClassManager();
  ~MixerClassManager();

  MixerClassManager(const MixerClassManager &) = delete;
  MixerClassManager &operator=(const MixerClassManager &) = delete;

private:
  struct MixerClass {
    const char *name;
    const Core::Portable::ComponentDescriptor *descriptor;
  };

  Core::Vector<MixerClass *> classes_;

  friend struct MixerClassManagerLifetimeProbe;
};

} // namespace Presonus

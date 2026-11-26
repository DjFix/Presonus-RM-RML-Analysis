#pragma once

#include "core/public/corevector.h"

namespace Core::Portable {
class ComponentDescriptor;
}

namespace Presonus {

class MixerClassManager {
  struct MixerClass {
    const char *name;
    const Core::Portable::ComponentDescriptor *descriptor;
  };

public:
  MixerClassManager();
  ~MixerClassManager();

  // Portable declarations. The original ordinary return types are unresolved.
  const MixerClass *getMixerClass(const char *name) const;
  bool isMixerClass(const char *name) const;

  MixerClassManager(const MixerClassManager &) = delete;
  MixerClassManager &operator=(const MixerClassManager &) = delete;

private:
  Core::Vector<MixerClass *> classes_;

  friend struct MixerClassManagerLifetimeProbe;
};

} // namespace Presonus

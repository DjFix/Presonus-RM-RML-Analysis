#pragma once
#include "core/public/corevector.h"
#include "presonus/surface/sl_mixer_encoder.hpp"

namespace presonus::mixer {
struct MappableMixerAccess;
}

namespace Presonus {
class SLChannelBase;
class IColorConverter;
class IPresetHandler;

// Partial portable source model of observed defaults, borrowed observer
// dispatch and lifecycle. Original inheritance, virtual layout and ordinary
// return declarations remain unresolved. SLChannelBase* and int are source-port
// choices, not recovered declarations.
class MappableMixer {
public:
  MappableMixer();
  ~MappableMixer();
  void sendObjectChangeMessage(IMixerComponentObserver::ObjectChangeMessage);
  // Source-port binding, borrowed for the lifetime of any use.
  IColorConverter *getColorConverter() const;
  virtual void setColorConverter(IColorConverter *converter);

  // Borrowed; the handler must outlive its use by this mixer.
  virtual void setPresetHandler(IPresetHandler *handler);
  IPresetHandler *getPresetHandler() const;

  SLChannelBase *getSelectedGeq() const;
  int countAllChannels() const;
  SLChannelBase *getChannelIndexed(int index) const;

private:
  friend struct presonus::mixer::MappableMixerAccess;
  Core::Vector<IMixerComponentObserver *> observers_;
  IColorConverter *colorConverter_ = nullptr;
  IPresetHandler *presetHandler_ = nullptr;
};
} // namespace Presonus

// Independent source-port access; does not claim an original registration API.
namespace presonus::mixer {
struct MappableMixerAccess {
  static Core::Vector<Presonus::IMixerComponentObserver *> &
  observers(Presonus::MappableMixer &mixer) {
    return mixer.observers_;
  }
};
} // namespace presonus::mixer

#pragma once

namespace Presonus {
class SLChannelBase;
class IColorConverter;

// Partial portable source model of three observed default operations. Original
// inheritance, virtual layout and ordinary return declarations remain
// unresolved. SLChannelBase* and int are source-port choices, not recovered
// declarations.
class MappableMixer {
public:
  // Source-port binding, borrowed for the lifetime of any use.
  IColorConverter *getColorConverter() const;
  virtual void setColorConverter(IColorConverter *converter);

  SLChannelBase *getSelectedGeq() const;
  int countAllChannels() const;
  SLChannelBase *getChannelIndexed(int index) const;

private:
  IColorConverter *colorConverter_ = nullptr;
};
} // namespace Presonus

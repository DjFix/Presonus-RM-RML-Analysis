#pragma once

namespace Presonus {
class SLChannelBase;

// Partial portable source model of three observed default operations. Original
// inheritance, virtual layout and ordinary return declarations remain
// unresolved. SLChannelBase* and int are source-port choices, not recovered
// declarations.
class MappableMixer {
public:
  SLChannelBase *getSelectedGeq() const;
  int countAllChannels() const;
  SLChannelBase *getChannelIndexed(int index) const;
};
} // namespace Presonus

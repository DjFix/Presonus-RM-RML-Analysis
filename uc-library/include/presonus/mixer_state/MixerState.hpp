#pragma once
#include <cstdint>

namespace Presonus {
// Original type identity is encoded by mangling. Enumerator names and the
// original underlying declaration remain unresolved; portable domain is int32.
enum ChannelType : int {};

// Independent semantic storage, not an original ARM object representation.
// Nonzero link words are tested without dereferencing or inventing pointee
// types.
struct PortableMixerState {
  std::uint32_t masterWord = 0;
  std::uint32_t slaveWord = 0;
  bool hasGeqConfiguration = false;
  std::uint32_t geqCountWord = 0;
};

class MixerClientComponentBase {
public:
  virtual bool isStereoChannelType(ChannelType type) const;
  // Portable int32 return choice. Original spelling/signedness is unresolved.
  virtual std::int32_t getNumGeqs() const;
  virtual std::int32_t getNumMixGeqs() const;
  // Observed 0/1/2 codes; original enum/return spelling is unresolved.
  std::uint32_t getCascadeState() const;
  PortableMixerState &portableState() { return state_; }

private:
  PortableMixerState state_;
};

// Original inheritance is not asserted by this portable declaration.
class MixerClientComponent {
public:
  bool isAggregateMeteringChannelType(ChannelType type) const;
};
} // namespace Presonus

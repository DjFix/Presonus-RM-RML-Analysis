#pragma once
#include <cstdint>
namespace Presonus::Dsp {
// Original application RTTI and PanelRegistrar secondary vtable establish these
// four observed pure slots. Returns are unencoded: void is a source-port
// choice except suspendControlSurfaces, whose observed low byte uses uint8_t
// as a source-port choice; its original return spelling remains unresolved. No
// original object layout, complete declaration or ARM vtable ABI is claimed.
class IAudioHAL {
public:
  virtual void resetBoard(int mode, int board) = 0;
  virtual void enableDACs(bool enabled, bool clock, int board) = 0;
  virtual void enableAMP(bool enabled) = 0;
  virtual std::uint8_t suspendControlSurfaces(bool suspended) = 0;

protected:
  ~IAudioHAL() = default;
};
} // namespace Presonus::Dsp

#pragma once
namespace Presonus::UC {
class IFirmwareUpdateListener;
}
namespace Presonus {
// Original app RTTI/vtable: three pure slots, no virtual destructor.
// Return declarations are provisional source-port choices, not encoded by ELF.
class IDeviceDFU {
public:
  virtual bool isMounted() = 0;
  virtual bool isFirmwareCompatible(int) = 0;
  virtual bool updateFirmware(UC::IFirmwareUpdateListener *, int) = 0;

protected:
  ~IDeviceDFU() = default;
};
} // namespace Presonus

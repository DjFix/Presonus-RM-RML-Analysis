#pragma once
#include "core/public/gui/corebitmapdata.h"
#include <cstdint>
namespace Presonus {
struct DisplayCommand;
// Observed fields, portable storage/alignment; original declaration names
// unknown.
struct DisplayUpdate {
  unsigned char display;
  const Core::BitmapData *data;
  std::uint16_t x, y, width, height;
};
// Complete original3 pure-slot interface; return declarations provisional.
class IDisplayPort {
public:
  virtual int updateDisplay(DisplayUpdate &) = 0;
  virtual bool isDisplayBufferActive(const void *) = 0;
  virtual int sendDisplayCommands(unsigned char, const DisplayCommand *,
                                  int) = 0;

protected:
  ~IDisplayPort() = default; // Independent nonvirtual helper; no invented slot.
};
} // namespace Presonus

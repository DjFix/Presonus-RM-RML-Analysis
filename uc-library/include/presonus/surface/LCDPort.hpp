#pragma once
#include "core/public/corebuffer.h"
#include "core/public/gui/corebitmapdata.h"
#include "presonus/surface/IDisplayPort.hpp"
#include "presonus/surface/ScribbleStripMgr.hpp"
namespace Presonus {
namespace Surface {
// Portable source model only. Original return declarations and ARM class layout
// remain unresolved.
class LCDPort : public IDisplayPort {
public:
  LCDPort();
  virtual ~LCDPort();
  bool isDisplayBufferActive(const void *) override;
  int updateDisplay(DisplayUpdate &update);
  bool write(const char *path, const Core::BitmapData &data);
  int sendDisplayCommands(unsigned char display, const DisplayCommand *commands,
                          int count);

private:
  Core::IO::Buffer buffer;
  ScribbleStripMgr scribble;
};
} // namespace Surface
} // namespace Presonus

#pragma once
#include "core/public/gui/corebitmapdata.h"
#include <array>
namespace Presonus {
// Original namespace and encoded arguments; return declarations and ARM layout
// pending.
class ScribbleStripMgr {
public:
  ScribbleStripMgr();
  int writeToScribbleStrip(int display, const Core::BitmapData &data);
  void txCommandDataArray(int fd, unsigned char command, unsigned char *data,
                          int count);
  void initDisplayModules();

private:
  std::array<unsigned char, 768> buffer;
};
} // namespace Presonus

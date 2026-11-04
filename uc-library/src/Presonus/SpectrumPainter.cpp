#include "presonus/SpectrumPainter.hpp"
namespace Presonus {
Core::TRect<int> SpectrumPainter::getLastDrawnRect() const { return last_; }
} // namespace Presonus

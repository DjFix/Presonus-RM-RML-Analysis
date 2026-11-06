#include "presonus/GridPainter.hpp"
namespace Presonus {
GridPainter::GridPainter(IBackgroundGridProvider &provider)
    : first_(ownedFirst_), second_(ownedSecond_), provider_(&provider) {}
GridPainter::~GridPainter() = default;
} // namespace Presonus

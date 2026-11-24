#include "presonus/surface/MainScreenComponent.hpp"
#include "presonus/PageComponent.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include <cstdint>
namespace Presonus::Surface {
void MainScreenComponent::init(MappingComponent *value) { bindMapping(value); }

MainScreenComponent::~MainScreenComponent() = default;
bool MainScreenComponent::canGoBack(const PageComponent &from,
                                    const PageComponent &to) const {
  int tag = from.getPageTag();
  if ((tag >= 14 && tag <= 16) || tag == 25) {
    const auto other = static_cast<std::uint32_t>(to.getPageTag());
    return other > 24 || ((std::uint32_t{1} << other) & 0x101c000u) == 0;
  }
  return tag != -1000 && tag != 7 && tag != 28;
}
void MainScreenComponent::onSelectedChannelChanged() {
  auto tag = getCurrentPageTag();
  if ((static_cast<std::uint32_t>(tag) - 14u) <= 2u || tag == 20 || tag == 30 ||
      tag == 29 || tag == 21)
    return;
  showStartPage();
}
int MainScreenComponent::getStartPageTag() const { return 0; }
bool MainScreenComponent::displayEncoderAssignmentLocked() const {
  return getCurrentPageTag() != getStartPageTag();
}
void MainScreenComponent::pageAboutToShow(const PageComponent &page,
                                          const PageComponent *previous) {
  if (!previous || !mapping_)
    return;
  const bool fromPreamps = previous->getPageTag() == 3;
  const int previousTag = previous->getPageTag();
  if (fromPreamps || page.getPageTag() == 3) {
    mapping_->setPreampsMeterMode(!fromPreamps);
    return;
  }
  const bool fromGeq = previousTag == 29;
  if (fromGeq || page.getPageTag() == 29)
    mapping_->setGeqMode(!fromGeq);
}

} // namespace Presonus::Surface

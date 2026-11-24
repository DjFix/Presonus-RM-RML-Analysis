#include "presonus/surface/AudioUtilitiesPage.hpp"
namespace Presonus::Surface {
AudioUtilitiesPage::AudioUtilitiesPage(const char *formName, int tag)
    : PageComponent("audioUtilititesPage", formName, tag) {}
AudioUtilitiesPage::~AudioUtilitiesPage() = default;
} // namespace Presonus::Surface

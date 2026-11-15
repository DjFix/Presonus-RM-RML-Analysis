#include "presonus/panel/JoinNetworkPage.hpp"
namespace Presonus::Panel {
void JoinNetworkPage::recall() {
  tree_.getParameterByTag(8)->fromString("", false);
}
} // namespace Presonus::Panel

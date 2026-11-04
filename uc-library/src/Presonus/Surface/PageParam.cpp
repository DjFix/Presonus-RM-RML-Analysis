#include "presonus/surface/PageParam.hpp"
namespace Presonus::Surface {
void PageParam::init(const char *page, const char *parameter) {
  text_.append("page:");
  text_.append(page);
  text_.append(".");
  text_.append(parameter);
}
} // namespace Presonus::Surface

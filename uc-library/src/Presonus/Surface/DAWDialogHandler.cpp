#include "presonus/surface/DAWDialogHandler.hpp"
namespace {
// Observed original ARM descriptor records, expressed using actual CCL types.
// Static contiguous records are borrowed by the provider (ownsInfo=false).
const Core::Portable::ParamInfo dialogParameters[] = {
    PARAM_TOGGLE(100, "dialogActive", 0, nullptr, 0),
    PARAM_INT(101, "numButtons", 1, 3, 1, nullptr, nullptr, 0, 0),
    PARAM_STRING(102, "dialogTitle", 0),
    PARAM_STRING(103, "dialogText", 0),
    PARAM_STRING(104, "buttonTitle1", 0),
    PARAM_STRING(105, "buttonTitle2", 0),
    PARAM_STRING(106, "buttonTitle3", 0),
    PARAM_TOGGLE(107, "buttonPush1", 0, nullptr, 0),
    PARAM_TOGGLE(108, "buttonPush2", 0, nullptr, 0),
    PARAM_TOGGLE(109, "buttonPush3", 0, nullptr, 0)};
} // namespace
namespace Presonus::Surface {
DAWDialogHandler::DAWDialogHandler() : Core::Portable::Component("dialog") {
  paramList.add(dialogParameters, 10, false);
}
DAWDialogHandler::~DAWDialogHandler() = default;
} // namespace Presonus::Surface

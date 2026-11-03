#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include "core/portable/corepersistence.h"
#include "core/public/corestringbuffer.h"
#include <cstdlib>
#include <iostream>
#include <string>
using namespace Core;
using namespace Core::Portable;
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  std::string op = argv[1];
  if (op == "reset" && argc == 4) {
    ParamInfo info = ParamInfo PARAM_STRING(4, "accessCode", 0);
    StringParam param(info);
    param.setDefaultText(argv[3]);
    param.fromString(argv[2], false);
    param.resetValue(false);
    std::cout << param.getText().str();
  } else if (op == "text" && argc == 3) {
    ParamInfo info = ParamInfo PARAM_STRING(1, "text", 0);
    StringParam param(info);
    param.fromString(argv[2], false);
    CStringBuffer<32> text;
    param.toString(text.getBuffer(), 32);
    std::cout << text.str();
  } else if (op == "format" && argc == 4) {
    CStringBuffer<32> text;
    text.appendFormat(argv[2],
                      static_cast<int>(std::strtol(argv[3], nullptr, 10)));
    std::cout << text.str();
  } else if (op == "filename" && argc == 3) {
    FileName path(argv[2]);
    std::cout << path.str();
  } else if (op == "descend" && argc == 4) {
    FileName path(argv[2]);
    path.descend(argv[3]);
    std::cout << path.str();
  } else if (op == "append" && argc == 4) {
    FileName path(argv[2]);
    path.append(argv[3]);
    std::cout << path.str();
  } else if (op == "mkdir" && argc == 3) {
    return FileUtils::makeDirectory(argv[2]) ? 0 : 1;
  } else if (op == "save" && argc == 5) {
    Attributes attributes(AttributeAllocator::getDefault());
    attributes.set(argv[3], argv[4]);
    return ArchiveUtils::saveToFile(argv[2], attributes) ? 0 : 1;
  } else
    return 2;
  return 0;
}

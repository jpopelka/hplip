#include "CommonDefinitions.h"
#include "dj3320PrintModes.h"
#include "dj4100PrintModes.h"

PrintModeTable lidil_print_modes_table [] =
{
    {"dj3320", dj3320PrintModes, sizeof(dj3320PrintModes)/sizeof(PrintMode)},
    {"dj3600", dj3320PrintModes, sizeof(dj3320PrintModes)/sizeof(PrintMode)},
    {"dj4100", dj4100PrintModes, sizeof(dj4100PrintModes)/sizeof(PrintMode)},
};


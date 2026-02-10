import json
import yappi
import logging
import aiofiles

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def handle_profiling():
    profile_stats = yappi.get_func_stats()
    logger.info("========PROFILED STATS=======")
    async with aiofiles.open("yappi_stats.txt", "a") as file:
        # YFuncStats is not JSON serializable, so we write a string summary instead
        import io
        out = io.StringIO()
        profile_stats.print_all(out=out)
        await file.write(out.getvalue())
        await file.write("\n" + "="*30 + "\n")

    profile_stats_filename = "profile_stats"
    profile_stats_file_type = "pstat"
    logger.info(f"Saving profile stats to file {profile_stats_filename}..")
    profile_stats.save(f"{profile_stats_filename}.{profile_stats_file_type}", type=profile_stats_file_type)
    logger.info("Profile saved")
    return
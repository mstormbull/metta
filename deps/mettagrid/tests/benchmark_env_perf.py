import time

import hydra
import numpy as np
import pandas as pd
from omegaconf import OmegaConf
from tqdm import tqdm

global actions
global env


def test_performance(env, actions, duration):
    tick = 0
    num_actions = actions.shape[0]
    start = time.time()
    with tqdm(total=duration, desc="Running performance test") as pbar:
        while time.time() - start < duration:
            atns = actions[tick % num_actions]
            obs, rewards, terminated, truncated, infos = env.step(atns)
            tick += 1
            if tick % 100 == 0:
                pbar.update(time.time() - start - pbar.n)

    print_stats(env._c_env.get_episode_stats())
    sps = atns.shape[0] * tick / (time.time() - start)
    microseconds = 1 / sps * 1000000
    print(f"SPS: {sps:.2f} {microseconds:.4f} μs")


actions = {}
env = {}


@hydra.main(version_base=None, config_path="../configs", config_name="simple")
def main(cfg):
    # Run with c profile
    from cProfile import run

    global env

    print(OmegaConf.to_yaml(cfg))

    cfg.game.max_steps = 999999999
    env = hydra.utils.instantiate(cfg, cfg, render_mode="human", _recursive_=False)
    env.reset()
    global actions
    # num_agents = cfg.game.num_agents
    actions = []
    for _a in range(1024):
        actions.append(env.action_space.sample())
    actions = np.array(actions)

    test_performance(env, actions, 5)
    exit(0)

    run("test_performance(env, actions, 10)", "stats.profile")
    import pstats
    from pstats import SortKey

    p = pstats.Stats("stats.profile")
    p.sort_stats(SortKey.TIME).print_stats(25)
    exit(0)


def print_stats(stats):
    # Extract game_stats
    game_stats = stats["game"]

    # Extract agent_stats
    agent_stats = stats["agent"]

    # Calculate total, average, min, and max for each agent stat
    total_agent_stats = {}
    avg_agent_stats = {}
    min_agent_stats = {}
    max_agent_stats = {}
    num_agents = len(agent_stats)

    for agent_stat in agent_stats:
        for key, value in agent_stat.items():
            if key not in total_agent_stats:
                total_agent_stats[key] = 0
                min_agent_stats[key] = float("inf")
                max_agent_stats[key] = float("-inf")
            total_agent_stats[key] += value
            if value < min_agent_stats[key]:
                min_agent_stats[key] = value
            if value > max_agent_stats[key]:
                max_agent_stats[key] = value

    for key, value in total_agent_stats.items():
        avg_agent_stats[key] = value / num_agents

    # Sort the keys alphabetically
    sorted_keys = sorted(total_agent_stats.keys())

    # Create DataFrame for game_stats
    game_stats_df = pd.DataFrame(sorted(game_stats.items()), columns=["Stat", "Value"])

    # Create DataFrame for agent stats
    agent_stats_df = pd.DataFrame(
        {
            "Stat": sorted_keys,
            "Total": [total_agent_stats[key] for key in sorted_keys],
            "Average": [avg_agent_stats[key] for key in sorted_keys],
            "Min": [min_agent_stats[key] for key in sorted_keys],
            "Max": [max_agent_stats[key] for key in sorted_keys],
        }
    )

    # Print the DataFrames
    print("\nGame Stats:")
    print(game_stats_df.to_string(index=False))

    print("\nAgent Stats:")
    print(agent_stats_df.to_string(index=False))


if __name__ == "__main__":
    main()

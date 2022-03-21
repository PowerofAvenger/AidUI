import dp_resolver.resolver_rules as resolver_rules
import utils.utils as utils
from config import *

high_contrast_patterns = [class_dp["false_hierarchy"], class_dp["attention_distraction"], class_dp["default_choice"]]
high_size_diff_patterns = [class_dp["false_hierarchy"], class_dp["attention_distraction"], class_dp["default_choice"]]

def is_relative_height_beyond_threshold(height_diff_threshold, segment_height, neighbor_height):
    if abs(segment_height - neighbor_height) > height_diff_threshold:
        return True
    return False

def is_relative_width_beyond_threshold(width_diff_threshold, segment_width, neighbor_width):
    if abs(segment_width - neighbor_width) > width_diff_threshold:
        return True
    return False

def resolve_size(segment_dp_resolution, analysis_result, segment_id, neighbor):
    height_diff_threshold = 0.1
    width_diff_threshold = 0.0
    detected_patterns = list(analysis_result[segment_id]["text_analysis"].keys())
    relative_height = analysis_result[segment_id]["size_analysis"]["relative_height"]
    relative_width = analysis_result[segment_id]["size_analysis"]["relative_width"]
    for id in relative_height.keys():
        if id != segment_id and is_relative_height_beyond_threshold(height_diff_threshold, relative_height[segment_id], relative_height[id]):
            for pattern in detected_patterns:
                if pattern in high_size_diff_patterns:
                    segment_dp_resolution[pattern]["votes"] += 0.5
                    segment_dp_resolution[pattern]["vote_from"][3] = 1
    for id in relative_width.keys():
        if id != segment_id and is_relative_width_beyond_threshold(width_diff_threshold, relative_width[segment_id], relative_width[id]):
            for pattern in detected_patterns:
                if pattern in high_size_diff_patterns:
                    segment_dp_resolution[pattern]["votes"] += 0.5
                    segment_dp_resolution[pattern]["vote_from"][3] = 1
    return segment_dp_resolution

def resolve_visual(segment_dp_resolution, analysis_result, segment_id, neighbor):
    detected_patterns = list(analysis_result[segment_id]["text_analysis"].keys())
    opacity = analysis_result[segment_id]["visual_analysis"]["opacity"]
    if neighbor:
        opacity_neighbor = analysis_result[neighbor]["visual_analysis"]["opacity"]
        if opacity != opacity_neighbor:
            for pattern in detected_patterns:
                if pattern in high_contrast_patterns:
                    segment_dp_resolution[pattern]["votes"] += 1
                    segment_dp_resolution[pattern]["vote_from"][2] = 1
    return segment_dp_resolution

def resolve_text(segment_dp_resolution, analysis_result, segment_id, neighbor=False):
    detected_patterns = list(analysis_result[segment_id]["text_analysis"].keys())
    detected_patterns_neighbor = []
    if neighbor:
        detected_patterns_neighbor = list(analysis_result[neighbor]["text_analysis"].keys())
    for pattern in detected_patterns:
        # segment_dp_resolution[pattern] = 1
        if(pattern not in segment_dp_resolution.keys()):
            segment_dp_resolution[pattern] = {"votes": 1, "vote_from": [1, 0, 0, 0]}
        if len(detected_patterns_neighbor) != 0:
            if pattern in detected_patterns_neighbor:
                segment_dp_resolution[pattern]["votes"] += 1
                segment_dp_resolution[pattern]["vote_from"][1] = 1
    return segment_dp_resolution

def resolve_segment_dp(analysis_result, segment_id):
    neighbors = analysis_result[segment_id]["proximity_analysis"]["neighbors"]
    segment_dp_resolution = {}
    # comparing with neighbors for text, visual, spatial resolve
    for neighbor in neighbors:
        segment_dp_resolution = resolve_text(segment_dp_resolution, analysis_result, segment_id, neighbor)
        segment_dp_resolution = resolve_visual(segment_dp_resolution, analysis_result, segment_id, neighbor)
        resolve_size(segment_dp_resolution, analysis_result, segment_id, neighbor)
    # text resolve if there is no neighbor
    if len(neighbors) == 0:
        segment_dp_resolution = resolve_text(segment_dp_resolution, analysis_result, segment_id)
    # confidence calculation for each pattern
    for pattern, value in segment_dp_resolution.items():
        confidence = 0
        visual_vote = False
        spatial_vote = False
        # check if there is visual and/or spatial vote
        if pattern in high_contrast_patterns:
            visual_vote = True
        if pattern in high_size_diff_patterns:
            spatial_vote = True
        # calculate confidence
        if visual_vote or spatial_vote:
            if visual_vote and spatial_vote:
                confidence = sum(value["vote_from"]) / len(value["vote_from"])
            else:
                confidence = sum(value["vote_from"]) / 3
        else:
            confidence = sum(value["vote_from"]) / 2
        value["confidence"] = confidence
    return segment_dp_resolution

def resolve_ui_dp(segment_dp, object_detection_result):
    ui_dp = {}
    # resolve all segments information
    for segment_dp_resolution in segment_dp.values():
        for pattern in list(segment_dp_resolution.keys()):
            if pattern in list(ui_dp.keys()):
                ui_dp[pattern]["votes"] += segment_dp_resolution[pattern]["votes"]
                ui_dp[pattern]["confidence"] = max(ui_dp[pattern]["confidence"], segment_dp_resolution[pattern]["confidence"])
                # ui_dp[pattern]["confidence"] += segment_dp_resolution[pattern]["confidence"]
                # ui_dp[pattern]["avg_confidence"] = ui_dp[pattern]["confidence"] / ui_dp[pattern]["votes"]
            else:
                ui_dp[pattern] = {}
                ui_dp[pattern]["votes"] = segment_dp_resolution[pattern]["votes"]
                ui_dp[pattern]["confidence"] = segment_dp_resolution[pattern]["confidence"]
                # ui_dp[pattern]["confidence"] = segment_dp_resolution[pattern]["confidence"]
                # ui_dp[pattern]["avg_confidence"] = ui_dp[pattern]["confidence"] / ui_dp[pattern]["votes"]
    # augment object detection information
    if object_detection_result is not None:
        for potential_dp in object_detection_result["potential_dp_classes"]:
            if potential_dp in list(ui_dp.keys()):
                ui_dp[potential_dp]["votes"] += 1
                ui_dp[potential_dp]["confidence"] = (.80 * ui_dp[potential_dp]["confidence"]) + (.20 * object_detection_result["scores"])
                # ui_dp[potential_dp]["avg_confidence"] = ui_dp[potential_dp]["confidence"] / ui_dp[potential_dp]["votes"]
            else:
                ui_dp[potential_dp] = {}
                ui_dp[potential_dp]["votes"] = 1
                ui_dp[potential_dp]["confidence"] = object_detection_result["scores"]
                # ui_dp[potential_dp]["avg_confidence"] = ui_dp[potential_dp]["confidence"] / ui_dp[potential_dp]["votes"]
    return ui_dp

def resolve_dp(input_to_resolver):
    analysis_result = input_to_resolver["analysis_result"]
    object_detection_result = input_to_resolver["object_detection_result"]
    segment_dp = {}
    for segment_id in analysis_result.keys():
        segment_dp_resolution = resolve_segment_dp(analysis_result, segment_id)
        segment_dp[segment_id] = segment_dp_resolution
    # utils.print_dictionary(segment_dp)
    ui_dp = resolve_ui_dp(segment_dp, object_detection_result)
    # utils.print_dictionary(ui_dp)
    return ui_dp

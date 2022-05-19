import matplotlib.pyplot as plt

""" This file contains functions for plotting purposes.
    - Timeline plots show time evolution of selected quantities through phases.
    - Bar plots."""

# default size (might be adapted depending on your screen resolution)
default_size_factor = 1.

# folder to which figures are saved by default
folder_figures = 'Figures'

# fonts default sizes
VERY_SMALL_SIZE = 10
SMALL_SIZE = 14
MEDIUM_SIZE = 16
BIGGER_SIZE = 20

# default fonts for plot elements
plt.rc('font', size=MEDIUM_SIZE)  # controls default text sizes
plt.rc('axes', titlesize=MEDIUM_SIZE)  # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)  # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title


def plot_single_timeline(servicer, quantity, plan, starting_epoch, fig=None, ax=None, show=True, save=None,
                         annotate=False, **kwargs):
    """ Plot a single line-plot that show the evolution in time of a quantity of a servicer in a plan.
    The quantity needs to match a defined attribute of "get_" method of the servicer.
    This method is reused to plot multiple servicers in plot_multiple_timeline

     Args:
        servicer (Scenario.Fleet_module.Servicer): servicer object containing the information to be plotted
        quantity (str): string representing the quantity to be plotted (linked to phase methods and attr.)
        plan (Plan_module.Plan): plan object containing the information to be plotted
        starting_epoch (Datetime.datetime): starting epoch (represented as 0 in the plot)
        fig (matplotlib.Figure): (optional) figure to which the plot is added
        ax (matplotlib.Axes.axis): (optional) axis to which the plot is added
        show (boolean): (optional) if True, the plot is displayed
        save (str): (optional) name of file to save the plot to. If None, the file is not saved.
        annotate (boolean): (optional) if True, annotate the plot (print name of phases on top of points)
        **kwargs (): (optional) all other arguments are forwarded to 'plot'
    """
    if ax is None and fig is None:
        fig, ax = plt.subplots(figsize=(15*default_size_factor, 10*default_size_factor))

    # retrieve data using 'get_' method if available, if not retrieve directly the attribute
    data = servicer.get_attribute_history('get_' + quantity, plan)
    if data:
        data, time, txt = servicer.get_attribute_history('get_'+quantity, plan)
    if not data:
        data, time, txt = servicer.get_attribute_history(quantity, plan)
    data_to_plot = []
    time_reference = []
    data_point = None
    # go through data and format it to correct time
    for i in range(0, len(data)):
        data_point = data[i]
        data_to_plot.append(data_point.value)
        time_point = time[i]
        time_point.format = 'jd'
        time_reference.append(time_point.value)
        starting_epoch.format = 'jd'
    # reset time based on starting_epoch
    time_reference[:] = [time - starting_epoch.value for time in time_reference]
    # plot
    ax.plot(time_reference, data_to_plot, '-ob', **kwargs)
    # annotate if needed
    if annotate:
        for i, string in enumerate(txt):
            ax.annotate(string, (time_reference[i], data_to_plot[i]), fontsize=VERY_SMALL_SIZE, rotation=70.,
                        ha="left", va="bottom")
    # setup axis names, if the data has a unit attribute, it is added to the axis name
    if hasattr(data_point, 'unit'):
        ax.set_ylabel(str(quantity) + ' [' + str(data_point.unit) + ']')
    else:
        ax.set_ylabel(str(quantity) + ' [-]')
    ax.set_xlabel('Time [day]')
    plt.grid(True)
    if show:
        plt.show()
    if save:
        fig.savefig(folder_figures + '/' + save + '.png', bbox_inches='tight')


def plot_multiple_timeline(fleet, quantity, plan, starting_epoch, fig=None, ax=None, show=True, save=None,
                           annotate=False, **kwargs):
    """ Plot a series of lines that show the evolution in time of attributes of servicers from a fleet based on a plan.
    Uses the plot_single_timeline method.

    Args:
        fleet (Fleet): fleet of scenario to be plotted
        quantity (str): string representing the quantity to be plotted (linked to phase methods and attr.)
        plan (Plan): plan of scenario to be plotted
        starting_epoch (Datetime.datetime): starting epoch (represented as time 0 in the plot)
        fig (matplotlib.Figure): (optional) figure to which the plot is added
        ax (matplotlib.Axes.axis): (optional) axis to which the plot is added
        show (boolean): (optional) if True, the plot is displayed
        save (str): (optional) name of file to save the plot to. If None, the file is not saved.
        annotate (boolean): (optional) if True, annotate the plot (print values over points of the line)
        **kwargs (): (optional) additional arguments are forwarded to 'plot'
    """
    if ax is None and fig is None:
        fig, ax = plt.subplots(figsize=(15*default_size_factor, 10*default_size_factor))
    color_palette = plt.get_cmap("Dark2")

    # retrieve, format and plot data for each servicer in fleet, log servicer and current_kits id as legend
    legend_to_plot = []
    i = 0
    for _, servicer in fleet.servicers.items():
        plot_single_timeline(servicer, quantity, plan, starting_epoch, ax=ax, fig=fig,
                             annotate=annotate, show=False, color=color_palette(i), **kwargs)
        legend_to_plot.append(servicer.ID)
        # repeat operation for current_kits if any
        i += 1
        for _, kit in servicer.initial_kits.items():
            plot_single_timeline(kit, quantity, plan, starting_epoch, ax=ax, fig=fig,
                                 annotate=annotate, show=False, color=color_palette(i), **kwargs)
            legend_to_plot.append(kit.ID)
            i += 1
    ax.set_xlabel('Time [day]')
    plt.legend(legend_to_plot)
    if show:
        plt.show()
    if save:
        fig.savefig(folder_figures+'/'+save+'.png', bbox_inches='tight')


# def plot_bars(list_data, names, valfmt='{:.0f}', title=None, legend=None, show=True, save=None, xlabel=None,
#               offset_text=0., text_limit=10, ax=None, fig=None, **kwargs):
#     """ Plot horizontal stacked bars for a number of quantities for a number of items (lines).
#
#     Args:
#         list_data ([]): list of data sets to be plotted. Each data set is a list: one value for each line.
#                         eg. [[1.0, 2.1],[2.5, 4.2]], respectively dry masses and then wet masses for two servicers
#         names ([str]): list of names for the each data set.
#                        eg. ['dry mass', 'wet mass']
#         valfmt (str): (optional) the format of the annotations.
#                     This should use the string format method, e.g. "{:.2f}".
#         title (str): title of the plot
#         legend ([str]): list of strings that will display in legend. No legend if none.
#         show (boolean): if True, the plot is displayed
#         save (str): name of file to save the plot to. If None, the file is not saved.
#         xlabel (str): name of the x axis
#         offset_text (float): lateral offset used to tweak the position of the annotation
#         text_limit (float): lower limit under which annotations will not be shown
#         ax (matplotlib.axes.Axes): (optional) axis instance to which the heatmap is plotted.
#                                    If not provided, use current axes or create a new one.
#         fig (matplotlib.axis): fig of axis
#         **kwargs (): all other arguments are forwarded to `barh`
#     """
#     if ax is None and fig is None:
#         fig, ax = plt.subplots(figsize=(25 * default_size_factor, 1.5 * len(names)*default_size_factor))
#     local_color_palette = plt.get_cmap("Set3")
#
#     # iterate through data sets
#     offset = [0] * len(list_data[0])
#     legend_data = []
#     for j, data in enumerate(list_data):
#         y_pos = np.arange(len(names))
#         # sort data set units
#         try:
#             unit = data[0].unit
#         except AttributeError:
#             data = data * u.m/u.m
#             unit = data[0].unit
#         # get value to plot
#         to_plot = [d.value for d in data]
#         p = ax.barh(y_pos, to_plot, align='center', left=offset, color=local_color_palette(j%12), **kwargs)
#         legend_data.append(p[0])
#
#         # print annotations for each value in  a data set
#         for i, element in enumerate(data):
#             if element.value != 0:
#                 if element.value >= text_limit:
#                     ax.text(offset_text + offset[i] + element.value / 2, i, valfmt.format(element.value),
#                             fontsize=SMALL_SIZE, color='black')
#                 offset[i] += element.value
#                 ax.set_yticks(y_pos)
#
#     # setup x and y axis
#     ax.set_yticklabels(names, fontsize=SMALL_SIZE)
#     ax.invert_yaxis()
#     for tick in ax.xaxis.get_major_ticks():
#         tick.label.set_fontsize(SMALL_SIZE)
#     # put units in axis name if available
#     if unit != '':
#         ax.set_xlabel(xlabel + ' [' + str(unit) + ']', fontsize=SMALL_SIZE)
#     else:
#         ax.set_xlabel(xlabel, fontsize=SMALL_SIZE)
#     # if mentioned, print title and legend
#     if title:
#         ax.set_title(title, fontsize=MEDIUM_SIZE)
#     if legend:
#         ax.legend(legend_data, legend, loc='center left', bbox_to_anchor=(1, 0.5), fontsize=SMALL_SIZE)
#     # if specified, show and/or save the plot
#     if show:
#         plt.show()
#     if save:
#         fig.savefig(folder_figures + '/' + save + '.png', bbox_inches='tight')
#         plt.close()
#
#
# def plot_servicer_mass_summary(fleet, save=None, title='', offset_text=0, text_limit=10, ax=None, fig=None, **kwargs):
#     """ Plot a bar graph to summarises the mass budget for a set of scenarios.
#
#     Args:
#         architecture (dict of dict if Scenario): dictionary of dictionary of scenarios to be plotted
#                               The keys for each dictionary represents a tradespace parameters.
#                               The method expects two dictionary levels (so two parameters).
#         first_parameters (list of str): values of the first parameter for which the data will be plotted
#         second_parameters (list of str): values of the second parameter for which the data will be plotted
#         save (str): name of file to save the plot to. If None, the file is not saved.
#         rm_duplicates (boolean): if true, only one kit will be plotted
#         title (str): title of the plot
#         offset_text (float): custom offset between text and center of bars (adjust if text misaligned)
#         text_limit (float): lower limit under which values will not be shown
#         ax (matplotlib.axes.Axes): (optional) axis instance to which the heatmap is plotted.
#                                    If not provided, use current axes or create a new one.
#         fig (matplotlib.axis): fig of axis
#         **kwargs (): all other arguments are forwarded to `plot_bars`
#     """
#     # iterate through scenarios
#     output = []
#     line_id = []
#     for first_parameter, scenarios in architecture.items():
#         for second_parameter, scenario in scenarios.items():
#             if first_parameters:
#                 if first_parameter not in first_parameters:
#                     continue
#             if second_parameters:
#                 if second_parameter not in second_parameters:
#                     continue
#             module_names, temp_output, temp_servicer_id = scenario.fleet.get_mass_summary(rm_duplicates=rm_duplicates)
#             if not output:
#                 output = temp_output
#                 for k, temp_servicer_ID_element in enumerate(temp_servicer_id):
#                     line_id.append(temp_servicer_id[k])
#             else:
#                 for k, temp_servicer_ID_element in enumerate(temp_servicer_id):
#                     for j, element in enumerate(temp_output):
#                         output[j].append(element[k])
#                     line_id.append(temp_servicer_id[k])
#     if output:
#         plot_bars(output, line_id, title=title, xlabel='Mass', legend=module_names, valfmt='{:.0f}',
#                   offset_text=offset_text, save=save, text_limit=text_limit, ax=ax, fig=fig,  **kwargs)
#
#
# def plot_scenario_mass_summary(scenario, save=None, rm_duplicates=True, title=None, offset_text=0, text_limit=10,
#                                ax=None, fig=None, **kwargs):
#     """ Plot a bar graph to summarises the mass budget for a set of scenarios.
#
#     Args:
#         scenario (custom scenario): scenario t obe plotted
#                               The method expects two dictionary levels (so two parameters).
#         save (str): name of file to save the plot to. If None, the file is not saved.
#         rm_duplicates (boolean): if true, only one kit will be plotted
#         title (str): title of the plot
#         offset_text (float): custom offset between text and center of bars (adjust if text misaligned)
#         text_limit (float): lower limit under which values will not be shown
#         ax (matplotlib.axes.Axes): (optional) axis instance to which the heatmap is plotted.
#                                    If not provided, use current axes or create a new one.
#         fig (matplotlib.axis): fig of axis
#         **kwargs (): all other arguments are forwarded to `plot_bars`
#     """
#     # iterate through scenarios
#     list_data = []
#     data_names = []
#
#     # get mass summary information
#     data_set_name, data_set, servicers_id = scenario.fleet.get_mass_summary(rm_duplicates=rm_duplicates)
#
#     print(data_set, data_set_name, servicers_id)
#     # for each servicer, get
#     for i, servicer_id in enumerate(servicers_id):
#         plot_bars(data_set[i], data_set_name[i], title=title, xlabel='Mass', legend=None, valfmt='{:.0f}',
#                   offset_text=offset_text, save=save, text_limit=text_limit, ax=ax, fig=fig, **kwargs)
#
#
#
#
# def plot_pareto(architectures, quantity='total_cost', reference=None, title=None, legend=None,
#                 save=None, legend_loc='lower right', **kwargs):
#     """ Plot a Pareto front with a given quantity vs number of serviced targets. Available quantities are:
#             - total_cost
#             - cost_per_target
#             - program_duration
#             - recurring_cost_per_target
#     Args:
#         architectures (dict(dict(Scenario)): dictionary of dictionary of scenarios to be plotted
#                                                 Each level of identifier in dictionaries is a tradespace parameter.
#                                                 The method expects two dictionary levels (so two parameters).
#                                                 constellations eg.: # of targets per servicer and # of servicers
#         quantity (str): string identifier of quantity to be plotted for the scenario
#                         eg. total_cost
#         reference (Scenario): possible reference in front of which the data will be adimensionalized.
#         title (str): title of the plot
#         legend ([str]): list of strings that will display in legend. No legend if none.
#         legend_loc (str): location of legend box (upper, lower / right, left)
#         save (str): name of file to save the plot to. If None, the file is not saved.
#         **kwargs (): all other arguments are forwarded to `scatter`
#     """
# # colors and markers
# color_palette = plt.get_cmap("Dark2")
# marker_set = ['o', 's', 'D', '^', 'v']
#     # create subplot
#     fig, axes = plt.subplots(figsize=(default_size_factor * 10, default_size_factor * 5))
#
#     # iterate through scenarios
#     legend_data = []
#     for first_parameter_index, scenarios_dict in enumerate(architectures):
#         for second_parameter, scenarios in scenarios_dict.items():
#             number_of_serviced_targets = []
#             quantity_to_plot = []
#             marker_color = []
#             marker_labels = []
#             # build data set
#             for third_parameter, scenario in scenarios.items():
#                 marker_labels.append(str(third_parameter) + 'x' + str(second_parameter))
#                 marker_color.append(color_palette(first_parameter_index))
#                 number_of_serviced_targets.append(scenario.get_number_of_serviced_targets())
#                 if reference:
#                     if quantity == 'total_cost':
#                         quantity_to_plot.append(scenario.get_cost_per_target()
#                                                 * scenario.get_number_of_serviced_targets()
#                                                 / reference.get_cost_per_target()
#                                                 / reference.get_number_of_serviced_targets())
#                     elif quantity == 'cost_per_target':
#                         quantity_to_plot.append(scenario.get_cost_per_target() / reference.get_cost_per_target())
#                     elif quantity == 'program_duration':
#                         quantity_to_plot.append(scenario.plan.get_program_duration().to(u.year).value)
#                     elif quantity == 'recurring_cost_per_target':
#                         quantity_to_plot.append(scenario.get_cost_per_target(with_development=False)
#                                                 / reference.get_cost_per_target(with_development=False))
#                     else:
#                         raise Exception('Error in plotting pareto.')
#                 else:
#                     if quantity == 'total_cost':
#                         quantity_to_plot.append(scenario.get_cost_per_target()
#                                                 * scenario.get_number_of_serviced_targets() / 1000000)
#                     elif quantity == 'cost_per_target':
#                         quantity_to_plot.append(scenario.get_cost_per_target() / 1000000)
#                     elif quantity == 'program_duration':
#                         quantity_to_plot.append(scenario.plan.get_program_duration().to(u.year).value)
#                     elif quantity == 'recurring_cost_per_target':
#                         quantity_to_plot.append(scenario.get_cost_per_target(with_development=False) / 1000000)
#                     else:
#                         raise Exception('Error in plotting pareto.')
#
#             # plot data set
#             line = axes.scatter(quantity_to_plot, number_of_serviced_targets, c=marker_color,
#                                 marker=marker_set[first_parameter_index], **kwargs)
#             if len(legend_data) <= first_parameter_index:
#                 legend_data.append(line)
#
#             # annotate
#             for l, txt in enumerate(marker_labels):
#                 axes.annotate(txt, (quantity_to_plot[l], number_of_serviced_targets[l] + 0.2),
#                               color=marker_color[l], fontsize=VERY_SMALL_SIZE)
#
#     # title and label axis
#     if title:
#         axes.set_title(title, fontsize=MEDIUM_SIZE)
#     if quantity == 'total_cost':
#         plt.xlabel('Total scenario cost w.r.t. reference scenario [-]')
#     elif quantity == 'cost_per_target':
#         plt.xlabel('Cost per removal w.r.t. reference scenario [-]')
#     elif quantity == 'program_duration':
#         plt.xlabel('Total scenario duration [days]')
#     elif quantity == 'recurring_cost_per_target':
#         plt.xlabel('Cost per removal [MEuros]')
#     else:
#         raise Exception('Error in plotting pareto.')
#     plt.ylabel('Number of serviced targets [-]')
#
#     # legend
#     if legend:
#         axes.legend(legend_data, legend, loc=legend_loc, fontsize=SMALL_SIZE)
#
#     # grid and ticks
#     plt.grid(True, which='major')
#     plt.minorticks_on()
#     plt.grid(True, which='minor', linestyle=':', linewidth='0.5')
#
#     # adjust to window
#     plt.subplots_adjust(left=0.1, bottom=0.15, right=0.95, top=0.95)
#
#     # show plot
#     plt.show()
#
#     # saving
#     if save:
#         fig.savefig(folder_figures + '/' + save + '.png', bbox_inches='tight')
#
#
# def plot_servicer_cost_summary(architecture, first_parameters=None, second_parameters=None, save=None,
#                                rm_duplicates=True, title='', offset_text=0, text_limit=10, ax=None, fig=None,
#                                **kwargs):
#     """ Plot a bar graph to summarises the mass budget for a set of scenarios.
#
#     Args:
#         architecture (dict of dict if Scenario): dictionary of dictionary of scenarios to be plotted
#                               The keys for each dictionary represents a tradespace parameters.
#                               The method expects two dictionary levels (so two parameters).
#         first_parameters (list of str): values of the first parameter for which the data will be plotted
#         second_parameters (list of str): values of the second parameter for which the data will be plotted
#         save (str): name of file to save the plot to. If None, the file is not saved.
#         rm_duplicates (boolean): if true, only one kit will be plotted
#         title (str): title of the plot
#         offset_text (float): custom offset between text and center of bars (adjust if text misaligned)
#         text_limit (float): lower limit under which values will not be shown
#         ax (matplotlib.axes.Axes): (optional) axis instance to which the heatmap is plotted.
#                                    If not provided, use current axes or create a new one.
#         fig (matplotlib.axis): fig of axis
#         **kwargs (): all other arguments are forwarded to `plot_bars`
#     """
#     # iterate through scenarios
#     output = []
#     line_id = []
#     for first_parameter, scenarios in architecture.items():
#         for second_parameter, scenario in scenarios.items():
#             if first_parameters:
#                 if first_parameter not in first_parameters:
#                     continue
#             if second_parameters:
#                 if second_parameter not in second_parameters:
#                     continue
#             module_names, temp_output, temp_servicer_id = scenario.fleet.get_recurring_cost_summary(rm_duplicates
#                                                                                                     =rm_duplicates)
#             if not output:
#                 output = temp_output
#                 for k, temp_servicer_ID_element in enumerate(temp_servicer_id):
#                     line_id.append(temp_servicer_id[k])
#             else:
#                 for k, temp_servicer_ID_element in enumerate(temp_servicer_id):
#                     for j, element in enumerate(temp_output):
#                         output[j].append(element[k])
#                     line_id.append(temp_servicer_id[k])
#     if output:
#         plot_bars(output, line_id, title=title, xlabel='Cost [kEuros]', legend=module_names, valfmt='{:.0f}',
#                   offset_text=offset_text, save=save, text_limit=text_limit, ax=ax, fig=fig,  **kwargs)
#
# def plot_cost_summary(architecture, first_parameters=None, second_parameters=None, save=None, title='', reference=None,
#                       offset_text=0., text_limit=10, ax= None, fig = None, **kwargs):
#     """ Plot a bar graph to summarises the cost budget for a set of scenarios.
#
#     Args:
#         architecture (dict of dict if Scenario): dictionary of dictionary of scenarios to be plotted
#                               The keys for each dictionary represents a tradespace parameters.
#                               The method expects two dictionary levels (so two parameters).
#         first_parameters (list of str): values of the first parameter for which the data will be plotted
#         second_parameters (list of str): values of the second parameter for which the data will be plotted
#         save (str): name of file to save the plot to. If None, the file is not saved.
#         title (str): title of the plot
#         reference (Scenario): possible reference in front of which the data will be adimensionalized.
#         offset_text (float): lateral offset used to tweak the position of the annotation
#         text_limit (float): lower limit under which values will not be shown
#         ax (matplotlib.axes.Axes): (optional) axis instance to which the heatmap is plotted.
#                                    If not provided, use current axes or create a new one.
#         fig (matplotlib.axis): fig of axis
#         **kwargs (): all other arguments are forwarded to `plot_bars`
#     """
#     # iterate through scenarios
#     output = []
#     line_id = []
#     for first_parameter, scenarios in architecture.items():
#         for second_parameter, scenario in scenarios.items():
#             if first_parameters:
#                 if first_parameter not in first_parameters:
#                     continue
#             if second_parameters:
#                 if second_parameter not in second_parameters:
#                     continue
#             module_names, temp_output = scenario.get_cost_summary()
#             if not output:
#                 output = temp_output
#                 line_id.append('')
#             else:
#                 for k, element in enumerate(temp_output):
#                     output[k].append(element[0])
#                 line_id.append('')
#     if reference:
#         ref_cost = reference.get_total_cost() / 1000000
#         for i, element_2 in enumerate(output):
#             for j, element in enumerate(element_2):
#                 output[i][j] = 100 * output[i][j] / ref_cost * u.pct
#
#     if output:
#         plot_bars(output, line_id, title=title,
#                   xlabel='Cost [MEuros]',
#                   legend=module_names, offset_text=offset_text, valfmt='{:.1f}', save=save, text_limit=text_limit,
#                   ax=ax, fig=fig,  **kwargs)
#
#
# #DEPRECATED
# def heatmap(data, row_labels, col_labels, ax=None, vmin=None, vmax=None, **kwargs):
#     """ Create a heatmap from a numpy array and two lists of labels.
#
#     Args:
#         data (list): a 2D list of shape (N, M)
#         row_labels ([], np.array): a list or array of length N with the labels for the rows
#         col_labels ([], np.array): a list or array of length M with the labels for the columns
#         ax (matplotlib.axes.Axes): (optional) axis instance to which the heatmap is plotted.
#                                    If not provided, use current axes or create a new one.
#         vmin (float): (optional) minimum range of colors (values bellow will all have same color)
#         vmax (float): (optional) maximum range of colors (values above will all have same color)
#         **kwargs (): all other arguments are forwarded to `imshow`
#
#     Return:
#         (matplotlib.image.AxesImage): heatmap
#     """
#     corrected_data = []
#     for k in range(0, len(data)):
#         if k == 0:
#             reference_width = len(data[k])
#         to_plot_line = data[k]
#         to_add = reference_width - len(to_plot_line)
#         for l in range(0, to_add):
#             to_plot_line.append(0)
#         corrected_data.append(to_plot_line)
#     corrected_data = np.array(corrected_data)
#
#     # create axis if not present
#     if not ax:
#         ax = plt.gca()
#
#     # plot the heatmap
#     img = ax.imshow(corrected_data, **kwargs, origin='lower', vmin=vmin, vmax=vmax)
#
#     # show all ticks
#     ax.set_xticks(np.arange(corrected_data.shape[1]))
#     ax.set_yticks(np.arange(corrected_data.shape[0]))
#
#     # label ticks with the respective list entries.
#     ax.set_xticklabels(col_labels)
#     ax.set_yticklabels(row_labels)
#
#     # let the horizontal axes labeling appear on top
#     ax.tick_params(top=False, bottom=True,
#                    labeltop=False, labelbottom=True)
#
#     # rotate the tick labels and set their alignment
#     plt.setp(ax.get_xticklabels(), rotation=0, ha="right",
#              rotation_mode="anchor")
#
#     return img
#
#
# #DEPRECATED
# def annotated_heatmap(img, data=None, data_txt=None, valfmt="{x:.2f}", textcolors=["black", "white"],
#                       threshold=None, **textkw):
#     """ A function to annotate a heatmap created with the heatmap method.
#
#     Args:
#         im (matplotlib.AxesImage): the image to be labeled
#         data (np.array): (optional) data used to annotate.  If None, the image's data is used.
#         data_txt (np.array) : (optional) list of labels to displays instead of the data values
#         valfmt (str): (optional) the format of the annotations.
#                       This should use the string format method, e.g. "$ {x:.2f}".
#         textcolors ([]): (optional) a list or array of two color specifications.
#                          The first is used for values below a threshold, the second for those above.
#         threshold (float): (optional) value in data units according to which the colors from textcolors are applied.
#                             If None (the default) uses the middle of the colormap as separation.
#         **textkw (): all other arguments are forwarded to `text`
#
#     Return:
#         ([]): list of text entries
#     """
#     # update fontsize
#     plt.rcParams.update({'font.size': SMALL_SIZE})
#
#     # get default data and text
#     if not isinstance(data, (list, np.ndarray)):
#         data = img.get_array()
#     if not isinstance(data_txt, (list, np.ndarray)):
#         data_txt = data
#
#     corrected_data_txt = []
#     for k in range(0, len(data)):
#         if k == 0:
#             reference_width = len(data[k])
#         to_write_line = data_txt[k]
#         to_add = reference_width - len(to_write_line)
#         for l in range(0, to_add):
#             to_write_line.append(0)
#         corrected_data_txt.append(to_write_line)
#     corrected_data_txt = np.array(corrected_data_txt)
#
#     # Normalize the threshold to the images color range.
#     if threshold is not None:
#         threshold = img.norm(threshold)
#     else:
#         threshold = img.norm(data.max()) / 2.
#
#     # Set default alignment to center, but allow it to be
#     # overwritten by textkw.
#     kw = dict(horizontalalignment="center",
#               verticalalignment="center")
#     kw.update(textkw)
#
#     # Get the formatter in case a string is supplied
#     if isinstance(valfmt, str):
#         valfmt = matplotlib.ticker.StrMethodFormatter(valfmt)
#
#     # Loop over the data and create a `Text` for each "pixel".
#     # Change the text's color depending on the data.
#     texts = []
#
#     for i in range(data.shape[0]):
#         for j in range(data.shape[1]):
#             kw.update(color=textcolors[int(img.norm(data[i, j]) > threshold)], fontsize=SMALL_SIZE)
#             text = img.axes.text(j, i, valfmt(corrected_data_txt[i, j], None), **kw)
#             texts.append(text)
#
#     return texts
#
#
# #DEPRECATED
# def plot_heatmap(scenarios_dict, quantities_list, scaling=1, suffix=None, vmin=None, vmax=None, cmap='GnBu',
#                  reference=None, valfmt='{x:.1f}', save=None, title=None, **kwargs):
#     """ Plot the results of a scenario as a heatmap. The results can be any quantity returned by a "get_" method.
#
#     Args:
#         scenarios_dict ([dict(dict(Scenario)]): list of recursive dictionary of scenarios to be plotted
#                                                 The keys for each dictionary represents a tradespace parameters.
#                                                 The method expects two dictionary levels (so two parameters).
#         quantities_list ([str]): list of quantities to be plotted.
#                                  They need to match a get_ method of a fleet, servicer, plan or phase class.
#         scaling (float): rescaling factor. The plotted data will be divided by this value.
#                          Used for instance to make thousands and millions more readable.
#         suffix (str): Possible suffix to print after the values displayed.
#                       If specified as None and data has a unit, the unit is used.
#         vmin (float): (optional) minimum range of colors (values bellow will all have same color)
#         vmax (float): (optional) maximum range of colors (values above will all have same color)
#         cmap (str): Identifier for the matplotlib color map to use.
#         reference (): possible reference in front of which the data will be adimensionalized.
#                       This can be given as a Scenario instance or a tuple of tradespace parameters.
#         valfmt (str): (optional) the format of the annotations.
#                       This should use the string format method, e.g. "$ {x:.2f}".
#         title ([[str]]): list of titles for each subplot
#         save (str): name of file to save the plot to. If None, the file is not saved.
#         **kwargs (): all other arguments are forwarded to `heatmap`
#     """
#     # get number of lines necessary to display all quantities
#     rows = len(scenarios_dict)
#     columns = len(quantities_list)
#
#     # retrieve reference scenario if given as parameters
#     if reference:
#         if reference.__class__.__name__ != 'Scenario':
#             reference = scenarios_dict[reference[0]][reference[1]]
#
#     # create figure and subsequent plots
#     fig, axes = plt.subplots(nrows=rows, ncols=columns, figsize=(5 * columns, 6 * rows))
#
#     plot_index = 1
#     for i, scenarios in enumerate(scenarios_dict):
#         for j, function_name in enumerate(quantities_list):
#             to_plot = []
#             to_write = []
#             suffix_to_print = suffix
#             # get data to plot and write while iterating through both tradespace parameters
#             for _, scenarios_parameter_1 in scenarios.items():
#                 to_plot_parameter_1 = []
#                 to_write_parameter_1 = []
#                 for _, scenarios_parameter_2 in scenarios_parameter_1.items():
#                     temp = scenarios_parameter_2.get_attribute(function_name)
#                     # get reference
#                     if reference:
#                         ref = reference.get_attribute(function_name)
#                         temp = temp / ref
#                     # transform time to human readable
#                     if isinstance(temp, Time):
#                         temp_write = str(temp)
#                         temp.format = 'jd'
#                         temp_plot = temp.value
#                     # get suffix, if none, get unit if data has it
#                     elif isinstance(temp, u.quantity.Quantity):
#                         temp = temp.decompose(bases=[u.kg, u.week]) / scaling
#                         if suffix_to_print is None:
#                             if isinstance(temp, u.Quantity):
#                                 suffix_to_print = str(temp.unit)
#                             else:
#                                 suffix_to_print = ''
#                         temp_plot = temp.value
#                         temp_write = temp_plot
#                     else:
#                         temp_plot = temp / scaling
#                         temp_write = temp_plot
#                     # build data to plot and write
#                     to_plot_parameter_1.append(temp_plot)
#                     to_write_parameter_1.append(temp_write)
#                 to_plot.append(to_plot_parameter_1)
#                 to_write.append(to_write_parameter_1)
#             param1 = scenarios.keys()
#             param2 = scenarios_parameter_1.keys()
#
#             # define subplot and plot
#             if rows > 1 and columns > 1:
#                 current_axes = axes[i, j]
#             elif rows == 1:
#                 current_axes = axes[i]
#             elif columns == 1:
#                 current_axes = axes[j]
#             else:
#                 print("Error in plotting.")
#
#             im = heatmap(to_plot, param1, param2, ax=current_axes,
#                          cmap=cmap, vmin=vmin, vmax=vmax, **kwargs)
#
#             # title and axis labels
#             current_axes.set_ylabel('Targets per\nservicer [-]')
#             current_axes.set_xlabel('Number of servicers [-]')
#             if title:
#                 current_axes.set_title(title[i][j])
#             else:
#                 current_axes.set_title(function_name)
#             plot_index += 1
#
#             # get threshold adapted for vmin and vmax
#             if vmin is None or vmax is None:
#                 thresh = None
#             else:
#                 thresh = vmin + (vmax + vmin) / 2
#
#             # do annotations
#             annotated_heatmap(im, data_txt=to_write, valfmt=valfmt + suffix_to_print, threshold=thresh)
#
#     plt.subplots_adjust(left=0.1, bottom=0.05, right=0.95, top=0.95, wspace=0.3, hspace=0.5)
#
#     plt.show()
#     # save plot
#     if save:
#         fig.savefig(folder_figures + '/' + save + '.png')
#
#
# # DEPRECATED
# def save_data(architectures, save_name='temp', append=False):
#     """ Writes key parameters to csv file. This method was used to output some data for another analysis.
#     """
#     rows = []
#     rows.append(['Technology', 'Architecture', 'Duration [year]', 'Serviced targets [-]', 'Servicers [-]', 'Cost per target [Euros]', 'Operational cost per target [Euros]'])
#     for architecture in architectures:
#         for _, scenarios in architecture.items():
#             for _, scenario in scenarios.items():
#                 tech = scenario.prop_type
#                 architecture = scenario.architecture
#                 duration = round(scenario.plan.get_program_duration().to(u.day).value)
#                 serviced = scenario.get_number_of_serviced_targets()
#                 servicers = len(scenario.fleet.servicers)
#                 cost_per_target = round(scenario.get_cost_per_target().value)
#                 op_cost = round(((scenario.plan.get_baseline_operations_cost(scenario.fleet) + scenario.plan.get_labour_operations_cost(scenario.fleet)) / serviced).value)
#                 rows.append([tech, architecture, duration, serviced, servicers, cost_per_target, op_cost])
#     if append:
#         with open(str(save_name) + '.csv', 'a') as writeFile:
#             writer = csv.writer(writeFile)
#             writer.writerows(rows)
#     else:
#         with open(str(save_name) + '.csv', 'w') as writeFile:
#             writer = csv.writer(writeFile)
#             writer.writerows(rows)
#     writeFile.close()

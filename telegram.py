import config
import html5lib
import requests
import telebot
from datetime import datetime, time, date
from bs4 import BeautifulSoup


# make a mistake in input -> RIP bot D:
bot = telebot.TeleBot(config.access_token)


def get_page(group, week=''):
    if week:
        week = str(week) + '/'
    url = '{domain}/{group}/{week}raspisanie_zanyatiy_{group}.htm'.format(
        domain=config.domain,
        week=week,
        group=group)
    response = requests.get(url)
    web_page = response.text
    return web_page


def get_schedule(web_page, day):
    soup = BeautifulSoup(web_page, "html5lib")
    # Методы find и find_all позволяют найти теги с указанными атрибутами.
    schedule_table = soup.find("table", attrs={"id": day})
    # Время проведения занятий
    times_list = schedule_table.find_all("td", attrs={"class": "time"})
    times_list = [time.span.text for time in times_list]
    # Место проведения занятий
    locations_list = schedule_table.find_all("td", attrs={"class": "room"})
    locations_list = [room.span.text for room in locations_list]     
    # Название дисциплин и имена преподавателей
    lessons_list = schedule_table.find_all("td", attrs={"class": "lesson"})
    lessons_list = [lesson.text.split('\n\n') for lesson in lessons_list]
    lessons_list = [', '.join([info for info in lesson_info if info]) for lesson_info in lessons_list]
    # Аудитории проведения занятий
    hall_list = schedule_table.find_all("dd", attrs={"class": "rasp_aud_mobile"})
    hall_list = [hall.text for hall in hall_list] 
    return times_list, locations_list, lessons_list, hall_list


def week_and_day(week_n, day_n):
    """
    Вспомогательная функция для get_near_lesson и get_tomorrow:
    определяет чётность недели, а также меняет неделю на следующую,
    если запрашиваем воскресенье (7day), и выдаёт понедельник (1day).
    """
    week = 1 if week_n % 2 else 2  # если номер недели нацело делится на 2 то четная если нет то нечетная
    week = 2 if (day_n == '7day' and week == 1) else 1  # если просим воскресенье > следующая неделя
    day = '1day' if day_n == '7day' else day_n  # если просим воскресенье > понедельник, в ином случае тот же
    return week, day


@bot.message_handler(commands=['monday','tuesday','wednesday','thursday','friday','saturday','sunday'])
def get_exact_day(message):
    """
    Расписание на один день недели для группы.
    /monday 1 K3142 - чётная неделя
    /tuesday 2 K3142 - нечётная неделя
    /wednesday 0 K3142 - обе недели вместе
    """
    day, week, group = message.text.split()
    if day in config.day_in_week.keys():  # /monday > day1, etc
        day_n = day  #  сохраняем для вывода, на случай, если занятий нет
        day = config.day_in_week.get(day)  # в config.py словарь day_in_week
    # try/except на случай, если занятий нет.
    try:
        web_page = get_page(group, week)
        times_list, locations_list, lessons_list, hall_list = get_schedule(web_page, day)
        resp = ''
        for time, location, lesson, hall in zip(times_list, locations_list, lessons_list, hall_list):
            resp += '<b>{}, {},</b> {}, {}\n'.format(time, hall, location, lesson)
    except:
        resp = 'Занятий в этот день ({}, неделя {}) нет.'.format(day_n, week)
    bot.send_message(message.chat.id, resp, parse_mode='HTML')


@bot.message_handler(commands=['tomorrow'])
def get_tomorrow(message):
    """
    Расписане для группы на завтра.
    /tomorrow K3142
    """
    _, group = message.text.split()
    today = datetime.now().isocalendar()  # ([0]2017,[1]week-22,[2]day-7)
    tomorrow = week_and_day(today[1], str(today[2]+1) + 'day')  # tuple (номер недели, номер завтрашнего дня + 'day')
    week, day = tomorrow[0], tomorrow[1]
    try:
        web_page = get_page(group, week)
        times_list, locations_list, lessons_list, hall_list = get_schedule(web_page, day)
        resp = ''
        for time, location, lesson, hall in zip(times_list, locations_list, lessons_list, hall_list):
            resp += '<b>{}, {},</b> {}, {}\n'.format(time, hall, location, lesson)
    except:
        resp = 'Занятий завтра нет.'
    bot.send_message(message.chat.id, resp, parse_mode='HTML')


@bot.message_handler(commands=['all'])
def get_all_week(message):
    """
    Расписание на всю неделю для группы.
    /all 1 K3142 - чётная неделя
    /all 2 K3142 - нечётная неделя
    """
    _, week, group = message.text.split()
    web_page = get_page(group, week)
    resp = ''
    for d in range(1,7):  # выводим расписание для всех 6 учебных дней в неделе
        day = str(d)+'day'
        try:  # try/except на случай, если занятий нет.
            times_list, locations_list, lessons_list, hall_list = get_schedule(web_page, day)
            day = config.weekday[d-1].upper()  # [d-1] т.к. range начинает с 1, а индексы с 0
        except:
            continue  # если занятий нет, цикл for заново, уже со следующим значением
        resp += '\n\n<b>'+day+'</b>\n'  # если занятия есть и все прошло гладко, выводим имя дня недели
        for time, location, lesson, hall in zip(times_list, locations_list, lessons_list, hall_list):
            resp += '<b>{}, {},</b> {}, {}\n'.format(time, hall, location, lesson)
    bot.send_message(message.chat.id, resp, parse_mode='HTML')
  

@bot.message_handler(commands=['soon'])
def get_near_lesson(message):
    """
    Ближайшее занятие для группы.
    /soon K3142
    """
    _, group = message.text.split()
    today = datetime.now().isocalendar()  # ([0]2017,[1]week-22,[2]day-7)
    week, day = week_and_day(today[1], str(today[2])+'day')
    current_time = datetime.strftime(datetime.now(), "%H:%M")  # current datetime to fit %H:%M format
    web_page = get_page(group, week)
    times_list, locations_list, lessons_list, hall_list = get_schedule(web_page, day)
    resp = ''
    resp += "<b>Время: </b>{}\n<b>Ближайшее занятие: </b>\n".format(current_time)
    for time, location, lesson, hall in zip(times_list, locations_list, lessons_list, hall_list):
        try:
        	# create a datetime object by use of strptime() and a corresponding format string
        	# times_list = schedule_table.find_all("td", attrs={"class": "time"})... >
        	# from the data on the page (...<td class="time"><span>13:30-15:00</span>...)
        	# then format the datetime object back to a string by use of the same format string.
        	# ! time[:4] - slicing a string. We get the first 4 chars in a string (start time of lesson).
            class_time = datetime.strftime(datetime.strptime(time[:4],"%H:%M"),"%H:%M")
            if class_time > current_time:
                resp += '<b>{}, {},</b> {}, {}\n'.format(time, hall, location, lesson)
                break
        except:
            resp = 'Пар в ближайшее время нет! Либо они днём.'
    bot.send_message(message.chat.id, resp, parse_mode='HTML')


if __name__ == '__main__':
    bot.polling(none_stop=True)

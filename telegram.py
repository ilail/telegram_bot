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
    week = 1 if week_n % 2 else 2
    day = '1day' if '7day' else day_n
    if day_n == '7day' and week == 1:
        week = 2
    else: week = 1
    return week, day


@bot.message_handler(commands=['monday','tuesday','wednesday','thursday','friday','saturday','sunday'])
def get_exact_day(message):
    day, week, group = message.text.split()
    if day in config.day_in_week.keys():
        day_n = day
        day = config.day_in_week.get(day)
    try:
        web_page = get_page(group, week)
        times_list, locations_list, lessons_list, hall_list = get_schedule(web_page, day)
        resp = ''
        for time, location, lesson, hall in zip(times_list, locations_list, lessons_list, hall_list):
            resp += '<b>{}, {}, {}</b>, {}\n'.format(time, hall, location, lesson)
    except:
        resp = 'Занятий в этот день ({}, неделя {}) нет.'.format(day_n, week)
    bot.send_message(message.chat.id, resp, parse_mode='HTML')


@bot.message_handler(commands=['tomorrow'])
def get_tomorrow(message):
    _, group = message.text.split()
    n = datetime.isocalendar(datetime.today())    #n = datetime.now().isocalendar()  #(0-2017,week-22,day-7)
    tomorrow = week_and_day(n[1], str(n[2]+1) + 'day')
    week, day = tomorrow[0], tomorrow[1]
    web_page = get_page(group, week)
    times_list, locations_list, lessons_list, hall_list = get_schedule(web_page, day)
    resp = ''
    for time, location, lesson, hall in zip(times_list, locations_list, lessons_list, hall_list):
        resp += '<b>{}, {}, {}</b>, {}\n'.format(time, hall, location, lesson)
    bot.send_message(message.chat.id, resp, parse_mode='HTML')


@bot.message_handler(commands=['all'])
def get_all_week(message):
    _, week, group = message.text.split()
    if week in config.week_list.values(): 
        week = week
    elif week in config.week_list.keys():
        week = config.week_list.get(week) 
    web_page = get_page(group, week)
    resp = ''
    for d in range(1,7):
        day = str(d)+'day'
        try:
            times_list, locations_list, lessons_list, hall_list = get_schedule(web_page, day)
            day = config.week[d-1].upper()
        except:
            continue
        resp += '\n\n<b>'+day+'</b>\n'
        for time, location, lesson, hall in zip(times_list, locations_list, lessons_list, hall_list):
            resp += '<b>{}, {}, {}</b>, {}\n'.format(time, hall, location, lesson)
    bot.send_message(message.chat.id, resp, parse_mode='HTML')
  

@bot.message_handler(commands=['soon'])
def get_near_lesson(message):
    _, group = message.text.split()
    date = datetime.now().isocalendar()
    week_n, day_n = date[1], date[2]
    week, day = week_and_day(week_n, day_n)
    current_time = datetime.strftime(datetime.now(), "%H:%M")
    web_page = get_page(group, week)
    times_list, locations_list, lessons_list, hall_list = get_schedule(web_page, day)
    resp = ''
    resp += "<b>Время: {}</b>\n<Занятие: \n".format(current_time)
    for time, location, lesson, hall in zip(times_list, locations_list, lessons_list, hall_list):
        try:
            class_time = datetime.strftime(datetime.strptime(time[:4],"%H:%M"),"%H:%M")
            if class_time > current_time:
                resp += '<b>{}, {}, {}</b>, {}\n'.format(time, hall, location, lesson)
                break
        except:
            resp = 'Пар в ближайшее время нет! Либо они "днём".'
    bot.send_message(message.chat.id, resp, parse_mode='HTML')


if __name__ == '__main__':
    bot.polling(none_stop=True)
